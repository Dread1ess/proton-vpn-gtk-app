"""
Preview-only stand-in for ``proton.vpn.session.servers``.

Models just enough of the real server data structures for the GTK widgets
(server list, search results, connection status) to render with fake data.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum
from typing import Any, Dict, List, Optional, Set

from ..dataclasses.servers import SecureCoreGroup


class TierEnum(IntEnum):
    FREE = 0
    PLUS = 1
    VISIONARY = 2


class ServerFeatureEnum(IntEnum):
    SECURE_CORE = 1
    P2P = 2
    TOR = 4
    STREAMING = 8
    SMART_ROUTING = 16


@dataclass
class LogicalServer:
    """A logical VPN server."""

    name: str = ""
    load: Optional[int] = 0
    exit_country: str = ""
    entry_country: str = ""
    exit_country_name: str = ""
    entry_country_name: str = ""
    location: str = ""
    features: Set[ServerFeatureEnum] = field(default_factory=set)
    under_maintenance: bool = False
    tier: TierEnum = TierEnum.FREE
    free: bool = True
    smart_routing: bool = False
    status: int = 1
    domain: str = ""


@dataclass
class Location:
    """A city/location within a country."""

    name: str = ""
    free: bool = True
    under_maintenance: bool = False
    features: Set[ServerFeatureEnum] = field(default_factory=set)
    smart_routing: bool = False
    servers: List[LogicalServer] = field(default_factory=list)
    free_servers: List[LogicalServer] = field(default_factory=list)
    paid_servers: List[LogicalServer] = field(default_factory=list)
    load: Optional[int] = None


@dataclass
class Country:
    """A country with its locations."""

    name: str = ""
    code: str = ""
    free: bool = True
    under_maintenance: bool = False
    features: Set[ServerFeatureEnum] = field(default_factory=set)
    smart_routing: bool = False
    locations: List[Location] = field(default_factory=list)
    servers: List[LogicalServer] = field(default_factory=list)
    free_locations: List[Location] = field(default_factory=list)
    paid_locations: List[Location] = field(default_factory=list)
    secure_core_group: Optional[SecureCoreGroup] = None


class ServerList:
    """An iterable collection of logical servers."""

    def __init__(self, servers: List[LogicalServer]):
        self._servers = list(servers)

    def __iter__(self):
        return iter(self._servers)

    def __bool__(self):
        return bool(self._servers)

    def __len__(self):
        return len(self._servers)

    def get(self, index: int) -> LogicalServer:
        return self._servers[index]

    def get_by_name(self, name: str) -> Optional[LogicalServer]:
        for server in self._servers:
            if server.name == name:
                return server
        return None

    @staticmethod
    def get_fastest_server(servers: List[LogicalServer]) -> Optional[LogicalServer]:
        available = [s for s in servers if not s.under_maintenance]
        if not available:
            return None
        return min(available, key=lambda s: s.load if s.load is not None else 0)

    @staticmethod
    def get_available_servers(
        servers: List[LogicalServer], user_tier: int
    ) -> List[LogicalServer]:
        return [s for s in servers if int(s.tier) <= int(user_tier)]

    def group_by_country(
        self, group_by_location: bool = True, include_free_servers: bool = True
    ) -> List[Country]:
        """Groups the servers by country (and optionally by location)."""
        grouped: Dict[str, Dict[str, Any]] = {}
        for server in self._servers:
            code = server.exit_country.upper()
            entry = grouped.setdefault(
                code, {"name": server.exit_country_name, "servers": []}
            )
            entry["servers"].append(server)

        countries: List[Country] = []
        for code, data in grouped.items():
            servers = data["servers"]
            countries.append(self._build_country(code, data["name"], servers))

        countries.sort(key=lambda c: (0 if c.free else 1, c.name))
        return countries

    @staticmethod
    def _build_country(code: str, name: str, servers: List[LogicalServer]) -> Country:
        def _features(items) -> Set[ServerFeatureEnum]:
            result: Set[ServerFeatureEnum] = set()
            for item in items:
                result.update(item.features)
            return result

        locations_by_name: Dict[str, List[LogicalServer]] = {}
        for server in servers:
            loc_name = server.location or name
            locations_by_name.setdefault(loc_name, []).append(server)

        locations: List[Location] = []
        for loc_name, loc_servers in locations_by_name.items():
            locations.append(
                Location(
                    name=loc_name,
                    free=any(s.free for s in loc_servers),
                    under_maintenance=all(s.under_maintenance for s in loc_servers),
                    features=_features(loc_servers),
                    smart_routing=any(s.smart_routing for s in loc_servers),
                    servers=loc_servers,
                    free_servers=[s for s in loc_servers if s.free],
                    paid_servers=[s for s in loc_servers if not s.free],
                )
            )

        sc_servers = [
            s for s in servers if ServerFeatureEnum.SECURE_CORE in s.features
        ]
        secure_core_group: Optional[SecureCoreGroup] = None
        if sc_servers:
            secure_core_group = SecureCoreGroup(
                servers=sc_servers,
                free=any(s.free for s in sc_servers),
                under_maintenance=all(s.under_maintenance for s in sc_servers),
            )

        return Country(
            name=name,
            code=code,
            free=any(s.free for s in servers),
            under_maintenance=all(s.under_maintenance for s in servers),
            features=_features(servers),
            smart_routing=any(s.smart_routing for s in servers),
            locations=locations,
            servers=servers,
            free_locations=[l for l in locations if l.free],
            paid_locations=[l for l in locations if not l.free],
            secure_core_group=secure_core_group,
        )
