"""
Preview-only stand-in for ``proton.vpn.connection.states``.
"""
from __future__ import annotations

from typing import Any, Optional


class ConnectionContext:
    """Context carried by a connection state."""

    def __init__(
        self,
        connection: Any = None,
        reconnection: bool = False,
        event: Any = None,
        connection_timestamp: Optional[float] = None,
    ):
        self.connection = connection
        self.reconnection = reconnection
        self.event = event
        self.connection_timestamp = connection_timestamp


class State:
    """Base connection state."""

    context: ConnectionContext

    def __init__(
        self,
        context: Optional[ConnectionContext] = None,
        forwarded_port: Optional[int] = None,
        connection_timestamp: Optional[float] = None,
    ):
        self.context = context if context is not None else ConnectionContext()
        self.forwarded_port = forwarded_port
        self.connection_timestamp = connection_timestamp


class Connected(State):
    pass


class Connecting(State):
    pass


class Disconnecting(State):
    pass


class Disconnected(State):
    pass


class Error(State):
    pass
