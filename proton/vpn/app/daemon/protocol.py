"""
Protocol constants and framing helpers for the Proton VPN daemon IPC.

Messages are JSON-RPC 2.0 encoded as newline-delimited JSON over a local
unix socket.

Copyright (c) 2026 Proton AG
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Optional

# Bump when a breaking change is introduced to the protocol. The GUI refuses
# to talk to a daemon whose protocol version does not match its own, so an
# old daemon + new GUI (or vice versa) fails loudly instead of silently.
PROTOCOL_VERSION = 1

SOCKET_ENV_VAR = "PROTONVPN_DAEMON_SOCKET"
DEFAULT_SOCKET_NAME = "protonvpn-daemon.sock"

# Method names.
METHOD_HANDSHAKE = "handshake"
METHOD_PING = "ping"
METHOD_LOGIN = "login"
METHOD_SUBMIT_2FA_CODE = "submit_2fa_code"
METHOD_LOGOUT = "logout"
METHOD_CONNECT_TO_FASTEST_SERVER = "connect_to_fastest_server"
METHOD_CONNECT_TO_SERVER = "connect_to_server"
METHOD_CONNECT_TO_COUNTRY = "connect_to_country"
METHOD_DISCONNECT = "disconnect"
METHOD_GET_STATUS = "get_status"
METHOD_GET_USER_LOGGED_IN = "get_user_logged_in"
METHOD_GET_ACCOUNT_NAME = "get_account_name"
METHOD_GET_APP_VERSION = "get_app_version"

# Server -> client notifications.
EVENT_CONNECTION_STATUS = "connection_status"
EVENT_DAEMON_READY = "daemon_ready"

# JSON-RPC error codes.
PARSE_ERROR = -32700
INVALID_REQUEST = -32600
METHOD_NOT_FOUND = -32601
INVALID_PARAMS = -32602
INTERNAL_ERROR = -32603
APP_ERROR = -32000
PROTOCOL_MISMATCH = -32001


class RpcError(Exception):
    """Base class for JSON-RPC errors, carrying the error code."""

    code = INTERNAL_ERROR

    def __init__(self, message: str, code: Optional[int] = None, data: Any = None):
        super().__init__(message)
        self.code = code or self.code
        self.data = data


class MethodNotFound(RpcError):
    code = METHOD_NOT_FOUND


class InvalidParams(RpcError):
    code = INVALID_PARAMS


class ProtocolMismatch(RpcError):
    code = PROTOCOL_MISMATCH


class ApplicationError(RpcError):
    code = APP_ERROR


@dataclass
class RpcMessage:
    """A parsed JSON-RPC 2.0 message (request, response or notification)."""

    jsonrpc: str
    method: Optional[str] = None
    id: Any = None
    params: Any = None
    result: Any = None
    error: Optional[dict] = None

    @property
    def is_request(self) -> bool:
        return self.method is not None and self.id is not None

    @property
    def is_notification(self) -> bool:
        return self.method is not None and self.id is None

    @property
    def is_response(self) -> bool:
        return self.method is None and self.id is not None


def encode_message(msg: RpcMessage) -> str:
    """Serializes an RpcMessage to a newline-delimited JSON string."""
    payload: dict = {"jsonrpc": msg.jsonrpc}
    if msg.id is not None:
        payload["id"] = msg.id
    if msg.method is not None:
        payload["method"] = msg.method
    if msg.result is not None:
        payload["result"] = msg.result
    if msg.error is not None:
        payload["error"] = msg.error
    if msg.params is not None:
        if msg.is_request:
            payload["params"] = msg.params
        else:
            payload["params"] = msg.params
    return json.dumps(payload) + "\n"


def encode_request(method: str, request_id: Any, params: Any = None) -> str:
    """Serializes a JSON-RPC 2.0 request."""
    return encode_message(
        RpcMessage(jsonrpc="2.0", method=method, id=request_id, params=params)
    )


def encode_notification(method: str, params: Any = None) -> str:
    """Serializes a JSON-RPC 2.0 notification (no id)."""
    return encode_message(
        RpcMessage(jsonrpc="2.0", method=method, params=params)
    )


def encode_result(request_id: Any, result: Any) -> str:
    """Serializes a JSON-RPC 2.0 success response."""
    return encode_message(
        RpcMessage(jsonrpc="2.0", id=request_id, result=result)
    )


def encode_error(request_id: Any, code: int, message: str, data: Any = None) -> str:
    """Serializes a JSON-RPC 2.0 error response."""
    error = {"code": code, "message": message}
    if data is not None:
        error["data"] = data
    return encode_message(
        RpcMessage(jsonrpc="2.0", id=request_id, error=error)
    )


def decode_message(line: str) -> RpcMessage:
    """Parses a single newline-delimited JSON message."""
    try:
        payload = json.loads(line)
    except (ValueError, TypeError) as excp:
        raise ValueError("Invalid JSON payload") from excp

    if not isinstance(payload, dict) or payload.get("jsonrpc") != "2.0":
        raise ValueError("Invalid JSON-RPC message")

    return RpcMessage(
        jsonrpc=payload["jsonrpc"],
        method=payload.get("method"),
        id=payload.get("id"),
        params=payload.get("params"),
        result=payload.get("result"),
        error=payload.get("error"),
    )
