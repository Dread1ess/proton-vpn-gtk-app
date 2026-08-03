"""
Preview-only stand-in for ``proton.vpn.connection.events``.
"""
class ConnectionEvent:
    pass


class TunnelSetupFailed(ConnectionEvent):
    pass


class AuthDenied(ConnectionEvent):
    pass


class Timeout(ConnectionEvent):
    pass


class DeviceDisconnected(ConnectionEvent):
    pass


class MaximumSessionsReached(ConnectionEvent):
    pass


class Connecting(ConnectionEvent):
    pass


class Connected(ConnectionEvent):
    pass


class Disconnecting(ConnectionEvent):
    pass


class Disconnected(ConnectionEvent):
    pass


class ConnectingError(ConnectionEvent):
    pass


class ConnectedError(ConnectionEvent):
    pass


class DisconnectingError(ConnectionEvent):
    pass
