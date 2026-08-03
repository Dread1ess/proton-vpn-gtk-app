"""
Preview-only stand-in for ``proton.vpn.session.servers.server_list_fetcher``.
"""


class ServerListFetcher:
    """Stub fetcher; the preview harness builds its own fake server list."""

    def __init__(self, session=None, **kwargs):
        self._session = session

    def load_from_cache(self):
        raise NotImplementedError(
            "ServerListFetcher is stubbed in the preview harness. "
            "Use fake_data.build_fake_server_list() instead."
        )
