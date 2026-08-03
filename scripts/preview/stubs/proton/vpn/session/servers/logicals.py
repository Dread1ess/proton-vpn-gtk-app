"""
Preview-only stand-in for ``proton.vpn.session.servers.logicals``.
"""


def sort_servers_alphabetically_by_country_and_server_name(server):
    """Sorts servers by entry country name and then server name."""
    return (server.entry_country_name.lower(), server.name.lower())
