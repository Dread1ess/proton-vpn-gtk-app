"""
Preview-only stand-in for ``proton.vpn.connection.exceptions``.
"""


class ConnectionFailed(Exception):
    pass


class AuthenticationError(ConnectionFailed):
    pass


class VPNConnectionError(Exception):
    pass


class ConnectionTimeout(VPNConnectionError):
    pass


class TunnelSetupError(VPNConnectionError):
    pass
