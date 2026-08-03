"""
Generates a realistic fake server list for the preview harness.

The data is intentionally similar in shape to what the real Proton API returns
so the server list widget, search results and connection status all render
meaningful content.
"""
from __future__ import annotations

from proton.vpn.session.servers import (
    LogicalServer,
    ServerFeatureEnum,
    ServerList,
    TierEnum,
)


def _server(
    name: str,
    country_code: str,
    country_name: str,
    location: str,
    load: int,
    tier: TierEnum,
    features=(),
    smart_routing: bool = False,
    under_maintenance: bool = False,
    entry: tuple | None = None,
) -> LogicalServer:
    """Builds a logical server with sensible defaults."""
    entry_code, entry_name = entry or (country_code, country_name)
    return LogicalServer(
        name=name,
        load=load,
        exit_country=country_code,
        entry_country=entry_code,
        exit_country_name=country_name,
        entry_country_name=entry_name,
        location=location,
        features=set(features),
        under_maintenance=under_maintenance,
        tier=tier,
        free=tier == TierEnum.FREE,
        smart_routing=smart_routing,
    )


def build_fake_server_list() -> ServerList:
    """Returns a fake, fully populated server list."""
    free = TierEnum.FREE
    plus = TierEnum.PLUS

    servers = [
        # --- Free countries (shown first for free users) ---
        _server("NL#2", "NL", "Netherlands", "Amsterdam", 12, free),
        _server("NL#3", "NL", "Netherlands", "Amsterdam", 23, free),
        _server("NL#12", "NL", "Netherlands", "Rotterdam", 41, free),
        _server("CH#1", "CH", "Switzerland", "Zurich", 18, free),
        _server("CH#5", "CH", "Switzerland", "Zurich", 35, free),
        _server("CH#9", "CH", "Switzerland", "Geneva", 27, free),
        _server("JP#1", "JP", "Japan", "Tokyo", 55, free),
        _server("JP#6", "JP", "Japan", "Osaka", 62, free),
        _server("RO#1", "RO", "Romania", "Bucharest", 8, free),
        _server("PL#1", "PL", "Poland", "Warsaw", 14, free),

        # --- Paid countries ---
        _server(
            "US#42", "US", "United States", "New York", 31, plus,
            features=(ServerFeatureEnum.P2P,),
        ),
        _server(
            "US#51", "US", "United States", "New York", 48, plus,
            features=(ServerFeatureEnum.P2P, ServerFeatureEnum.TOR),
        ),
        _server(
            "US#77", "US", "United States", "Los Angeles", 22, plus,
            features=(ServerFeatureEnum.P2P,),
        ),
        _server(
            "US#88", "US", "United States", "Dallas", 67, plus,
            features=(ServerFeatureEnum.STREAMING,),
        ),
        _server(
            "US#120", "US", "United States", "Seattle", 40, plus,
            features=(ServerFeatureEnum.STREAMING, ServerFeatureEnum.P2P),
        ),
        _server(
            "UK#22", "GB", "United Kingdom", "London", 19, plus,
            features=(ServerFeatureEnum.P2P, ServerFeatureEnum.STREAMING),
        ),
        _server("UK#30", "GB", "United Kingdom", "London", 33, plus),
        _server("UK#31", "GB", "United Kingdom", "Manchester", 58, plus),
        _server(
            "DE#19", "DE", "Germany", "Frankfurt", 26, plus,
            features=(ServerFeatureEnum.P2P,),
        ),
        _server("DE#25", "DE", "Germany", "Frankfurt", 45, plus),
        _server(
            "SE#11", "SE", "Sweden", "Stockholm", 15, plus,
            features=(ServerFeatureEnum.P2P,),
        ),
        _server(
            "IS#3", "IS", "Iceland", "Reykjavik", 9, plus,
            features=(ServerFeatureEnum.P2P,),
        ),
        _server(
            "CA#8", "CA", "Canada", "Toronto", 29, plus,
            features=(ServerFeatureEnum.P2P, ServerFeatureEnum.STREAMING),
        ),
        _server("CA#14", "CA", "Canada", "Vancouver", 51, plus),
        _server(
            "HK#6", "HK", "Hong Kong", "Hong Kong", 63, plus,
            features=(ServerFeatureEnum.P2P, ServerFeatureEnum.STREAMING),
        ),
        _server(
            "SG#2", "SG", "Singapore", "Singapore", 71, plus,
            features=(ServerFeatureEnum.P2P,),
        ),
        _server(
            "AU#5", "AU", "Australia", "Sydney", 84, plus,
            features=(ServerFeatureEnum.STREAMING,),
        ),
        _server("FR#12", "FR", "France", "Paris", 21, plus),
        _server(
            "FR#15", "FR", "France", "Marseille", 36, plus,
            features=(ServerFeatureEnum.P2P,),
        ),
        _server(
            "NO#4", "NO", "Norway", "Oslo", 13, plus,
            features=(ServerFeatureEnum.P2P,),
        ),

        # --- Countries with secure core servers ---
        _server(
            "CH-SC#1", "CH", "Switzerland", "Zurich", 50, plus,
            features=(ServerFeatureEnum.SECURE_CORE,),
            entry=("SE", "Sweden"),
        ),
        _server(
            "CH-SC#2", "CH", "Switzerland", "Zurich", 61, plus,
            features=(ServerFeatureEnum.SECURE_CORE,),
            entry=("IS", "Iceland"),
        ),
        _server(
            "SE-SC#1", "SE", "Sweden", "Stockholm", 47, plus,
            features=(ServerFeatureEnum.SECURE_CORE,),
            entry=("CH", "Switzerland"),
        ),

        # --- Smart routing country (blocked in some regions) ---
        _server(
            "RU#1", "RU", "Russia", "Moscow", 74, plus,
            features=(ServerFeatureEnum.STREAMING,),
            smart_routing=True,
        ),

        # --- A country under maintenance ---
        _server(
            "ZA#1", "ZA", "South Africa", "Johannesburg", 100, plus,
            features=(ServerFeatureEnum.P2P,),
            under_maintenance=True,
        ),
    ]

    return ServerList(servers)
