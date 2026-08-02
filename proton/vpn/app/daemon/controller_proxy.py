"""
Maps JSON-RPC methods to calls on a Controller-like object.

The proxy is deliberately duck-typed: it works with the real
``proton.vpn.app.gtk.controller.Controller`` as well as with a fake
implementation used for development/tests. It never imports the Proton
backend directly, so the daemon can run its RPC layer standalone.

Copyright (c) 2026 Proton AG
"""
from __future__ import annotations

import asyncio
import inspect
from typing import Any, Callable, Dict, Optional

from proton.vpn.app.daemon import protocol


class ControllerProxy:
    """Resolves RPC method names to coroutine handlers over a controller."""

    def __init__(self, controller: Any):
        self._controller = controller

    def is_method_available(self, method: str) -> bool:
        return hasattr(self, f"_rpc_{method}")

    async def call(self, method: str, params: Any) -> Any:
        handler = getattr(self, f"_rpc_{method}", None)
        if handler is None:
            raise protocol.MethodNotFound(method)
        return await handler(params)

    # ---- handlers ---------------------------------------------------------

    async def _rpc_ping(self, params: Any) -> Any:
        return {"protocol_version": protocol.PROTOCOL_VERSION, "pong": True}

    async def _rpc_login(self, params: Any) -> Any:
        username = params["username"]
        password = params["password"]
        await self._await_future(
            self._controller.login(username, password)
        )
        return {"logged_in": self._controller.user_logged_in}

    async def _rpc_submit_2fa_code(self, params: Any) -> Any:
        code = params["code"]
        await self._await_future(self._controller.submit_2fa_code(code))
        return {"logged_in": self._controller.user_logged_in}

    async def _rpc_logout(self, params: Any) -> Any:
        await self._await_future(self._controller.logout())
        return None

    async def _rpc_connect_to_fastest_server(self, params: Any) -> Any:
        await self._await_future(
            self._controller.connect_to_fastest_server()
        )
        return self._serialize_status(self._controller.current_connection_status)

    async def _rpc_connect_to_server(self, params: Any) -> Any:
        await self._await_future(
            self._controller.connect_to_server(params.get("server_name"))
        )
        return self._serialize_status(self._controller.current_connection_status)

    async def _rpc_connect_to_country(self, params: Any) -> Any:
        await self._await_future(
            self._controller.connect_to_country(params["country_code"])
        )
        return self._serialize_status(self._controller.current_connection_status)

    async def _rpc_disconnect(self, params: Any) -> Any:
        await self._await_future(self._controller.disconnect())
        return None

    async def _rpc_get_status(self, params: Any) -> Any:
        return self._serialize_status(self._controller.current_connection_status)

    async def _rpc_get_user_logged_in(self, params: Any) -> Any:
        return {"logged_in": bool(self._controller.user_logged_in)}

    async def _rpc_get_account_name(self, params: Any) -> Any:
        return {"account_name": self._controller.account_name}

    async def _rpc_get_app_version(self, params: Any) -> Any:
        return {"app_version": self._controller.app_version}

    # ---- helpers ----------------------------------------------------------

    @staticmethod
    async def _await_future(future):
        """Awaits a concurrent.futures.Future inside the asyncio loop."""
        if inspect.isawaitable(future):
            await future
            return
        await asyncio.wrap_future(future)

    @staticmethod
    def _serialize_status(state: Any) -> Dict[str, Any]:
        """Serializes a connection state object into a plain dict.

        The state objects come from ``proton.vpn.connection.states`` and are
        duck-typed here via their class name to avoid a hard dependency.
        """
        state_name = type(state).__name__.lower()
        name = getattr(state, "name", None)
        if isinstance(name, str) and name:
            state_name = name.lower()
        context = getattr(state, "context", None)
        reconnecting = False
        if context is not None:
            try:
                reconnecting = bool(context.reconnection)
            except (AttributeError, TypeError):
                reconnecting = False
        return {
            "state": state_name,
            "reconnecting": reconnecting,
            "detail": getattr(state, "detail", None),
        }
