"""
JSON-RPC 2.0 server over a local unix socket.

Handles the connection lifecycle (handshake with protocol version check),
dispatches requests to the :class:`ControllerProxy`, and broadcasts
push events (connection status updates) to all connected clients.

Copyright (c) 2026 Proton AG
"""
from __future__ import annotations

import asyncio
import logging
import os
from typing import Any, Optional, Set

from proton.vpn.app.daemon import protocol
from proton.vpn.app.daemon.controller_proxy import ControllerProxy
from proton.vpn.app.daemon.protocol import (
    RpcError,
    decode_message,
    encode_error,
    encode_notification,
    encode_result,
)

logger = logging.getLogger(__name__)


class _ConnectionStatusEmitter:
    """Adapter that turns controller status updates into notifications.

    Registered on the controller the same way the GTK app registers widgets
    (``register_connection_status_subscriber``), but instead of updating a UI
    it forwards the state to every connected IPC client.
    """

    def __init__(self, broadcast: Any):
        self._broadcast = broadcast

    def connection_status_update(self, connection_state: Any):
        self._broadcast(
            encode_notification(
                protocol.EVENT_CONNECTION_STATUS,
                self._serialize(connection_state),
            )
        )

    @staticmethod
    def _serialize(state: Any) -> dict:
        return ControllerProxy._serialize_status(state)


class DaemonServer:
    """Runs the daemon IPC server for a single Controller-like object."""

    def __init__(self, controller: Any, socket_path: str):
        self._controller = controller
        self._socket_path = socket_path
        self._proxy = ControllerProxy(controller)
        self._server: Optional[asyncio.AbstractServer] = None
        self._clients: Set[asyncio.StreamWriter] = set()
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._emitter = _ConnectionStatusEmitter(self._schedule_broadcast)
        self._emitter_registered = False

    # ---- public API -------------------------------------------------------

    async def start(self) -> None:
        """Binds the unix socket and starts accepting connections."""
        if os.path.exists(self._socket_path):
            logger.warning("Removing stale socket %s", self._socket_path)
            os.unlink(self._socket_path)

        os.makedirs(os.path.dirname(self._socket_path) or ".", exist_ok=True)

        self._loop = asyncio.get_running_loop()
        self._server = await asyncio.start_unix_server(
            self._handle_client, path=self._socket_path
        )
        os.chmod(self._socket_path, 0o600)
        self._register_emitter()
        logger.info("Daemon listening on %s", self._socket_path)

    async def stop(self) -> None:
        """Stops accepting connections and shuts down clients."""
        if self._server is not None:
            self._server.close()
            await self._server.wait_closed()
            self._server = None
        for writer in list(self._clients):
            self._close_writer(writer)
        self._clients.clear()
        self._unregister_emitter()
        if os.path.exists(self._socket_path):
            try:
                os.unlink(self._socket_path)
            except FileNotFoundError:
                pass

    async def serve_forever(self) -> None:
        """Runs the server until stopped."""
        await self.start()
        try:
            # Keep the loop alive; clients run as separate tasks.
            while True:
                await asyncio.sleep(3600)
        except asyncio.CancelledError:
            await self.stop()
            raise

    # ---- connection handling ---------------------------------------------

    async def _handle_client(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        peer = writer.get_extra_info("peername")
        logger.debug("Client connected: %s", peer)
        try:
            if not await self._do_handshake(reader, writer):
                logger.debug("Handshake rejected for %s", peer)
                return
            self._clients.add(writer)
            self._broadcast_bytes(
                encode_notification(
                    protocol.EVENT_DAEMON_READY,
                    {"protocol_version": protocol.PROTOCOL_VERSION},
                )
            )
            logger.debug("Handshake ok, entering read loop for %s", peer)
            await self._read_loop(reader, writer)
        except asyncio.CancelledError:
            logger.debug("Client handler cancelled for %s", peer)
        except (ConnectionError, asyncio.IncompleteReadError):
            logger.debug("Client disconnected: %s", peer)
        except Exception as excp:  # pylint: disable=broad-except
            logger.exception("Client handler error for %s: %s", peer, excp)
        finally:
            self._clients.discard(writer)
            self._close_writer(writer)

    async def _do_handshake(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> bool:
        try:
            line = await asyncio.wait_for(reader.readline(), timeout=10)
        except (asyncio.TimeoutError, asyncio.IncompleteReadError):
            logger.debug("Handshake: no line received")
            self._close_writer(writer)
            return False

        logger.debug("Handshake: received %r", line)

        try:
            message = decode_message(line.decode("utf-8"))
        except (ValueError, UnicodeDecodeError) as excp:
            writer.write(encode_error(None, protocol.PARSE_ERROR, str(excp)).encode("utf-8"))
            await writer.drain()
            self._close_writer(writer)
            return False

        if message.method != protocol.METHOD_HANDSHAKE:
            writer.write(
                encode_error(
                    message.id,
                    protocol.INVALID_REQUEST,
                    "First message must be a handshake",
                ).encode("utf-8")
            )
            await writer.drain()
            self._close_writer(writer)
            return False

        params = message.params or {}
        client_version = params.get("protocol_version")
        if client_version != protocol.PROTOCOL_VERSION:
            writer.write(
                encode_error(
                    message.id,
                    protocol.PROTOCOL_MISMATCH,
                    "Protocol version mismatch",
                    {
                        "server_version": protocol.PROTOCOL_VERSION,
                        "client_version": client_version,
                    },
                ).encode("utf-8")
            )
            await writer.drain()
            self._close_writer(writer)
            return False

        writer.write(
            encode_result(
                message.id,
                {"protocol_version": protocol.PROTOCOL_VERSION},
            ).encode("utf-8")
        )
        await writer.drain()
        return True

    async def _read_loop(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        while True:
            line = await reader.readline()
            if not line:
                return  # EOF
            try:
                message = decode_message(line.decode("utf-8"))
            except (ValueError, UnicodeDecodeError) as excp:
                await self._send(
                    writer,
                    encode_error(None, protocol.PARSE_ERROR, str(excp)),
                )
                continue
            if message.is_request:
                asyncio.create_task(
                    self._dispatch(writer, message.id, message.method, message.params)
                )

    async def _dispatch(self, writer, request_id, method, params) -> None:
        if method == protocol.METHOD_HANDSHAKE:
            await self._send(
                writer,
                encode_error(request_id, protocol.INVALID_REQUEST, "Already handshaken"),
            )
            return
        try:
            result = await self._proxy.call(method, params)
        except RpcError as excp:
            await self._send(writer, encode_error(request_id, excp.code, str(excp)))
        except KeyError as excp:
            await self._send(
                writer,
                encode_error(
                    request_id, protocol.INVALID_PARAMS, f"Missing parameter: {excp}"
                ),
            )
        except Exception as excp:  # pylint: disable=broad-except
            logger.exception("Error handling %s: %s", method, excp)
            await self._send(
                writer, encode_error(request_id, protocol.INTERNAL_ERROR, str(excp))
            )
        else:
            await self._send(writer, encode_result(request_id, result))

    async def _send(self, writer: asyncio.StreamWriter, data: str) -> None:
        try:
            writer.write(data.encode("utf-8"))
            await writer.drain()
        except (ConnectionError, RuntimeError):
            self._close_writer(writer)

    def _broadcast_bytes(self, data: str) -> None:
        for writer in list(self._clients):
            try:
                writer.write(data.encode("utf-8"))
                asyncio.get_running_loop().call_soon(self._flush, writer)
            except (ConnectionError, RuntimeError):
                self._close_writer(writer)

    def _schedule_broadcast(self, data: str) -> None:
        """Thread-safe broadcast: status updates arrive from controller threads."""
        if self._loop is None:
            return
        self._loop.call_soon_threadsafe(self._broadcast_bytes, data)

    @staticmethod
    def _flush(writer: asyncio.StreamWriter) -> None:
        try:
            asyncio.get_running_loop().create_task(writer.drain())
        except (ConnectionError, RuntimeError):
            pass

    @staticmethod
    def _close_writer(writer: asyncio.StreamWriter) -> None:
        try:
            writer.close()
        except (ConnectionError, RuntimeError):
            pass

    # ---- controller wiring ------------------------------------------------

    def _register_emitter(self) -> None:
        register = getattr(self._controller, "register_connection_status_subscriber", None)
        if callable(register):
            try:
                register(self._emitter)
                self._emitter_registered = True
            except Exception:  # pylint: disable=broad-except
                logger.exception("Failed to register status emitter")

    def _unregister_emitter(self) -> None:
        if not self._emitter_registered:
            return
        unregister = getattr(
            self._controller, "unregister_connection_status_subscriber", None
        )
        if callable(unregister):
            try:
                unregister(self._emitter)
            except Exception:  # pylint: disable=broad-except
                logger.exception("Failed to unregister status emitter")
        self._emitter_registered = False
