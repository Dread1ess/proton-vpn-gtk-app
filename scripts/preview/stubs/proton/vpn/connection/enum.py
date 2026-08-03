"""
Preview-only stand-in for ``proton.vpn.connection.enum``.
"""
from enum import IntEnum


class KillSwitchSetting(IntEnum):
    OFF = 0
    ON = 1
    PERMANENT = 2
