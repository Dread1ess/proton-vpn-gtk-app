"""
Preview-only stand-in for ``proton.vpn.session.dataclasses.servers``.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, List


@dataclass
class SecureCoreGroup:
    """A group of secure core servers routed through an entry country."""

    servers: List[Any] = field(default_factory=list)
    free: bool = True
    under_maintenance: bool = False
