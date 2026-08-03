"""
Preview-only stand-in for ``proton.vpn.connection`` (private package).
Provides just enough of the state machine surface that the GTK widgets use.
"""
from . import states, events, enum, exceptions  # noqa: F401
from .states import (  # noqa: F401
    State,
    Connected,
    Connecting,
    Disconnecting,
    Disconnected,
    Error,
    ConnectionContext,
)
