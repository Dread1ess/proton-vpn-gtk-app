"""
In-memory fake controller used for development and demos of the vertical
slice (login -> connect -> disconnect -> status) without the Proton backend.

It implements the same duck-typed interface as the real GTK Controller that
``ControllerProxy`` relies on.
"""
from __future__ import annotations

import threading
import time
from concurrent.futures import Future, ThreadPoolExecutor
from typing import Dict, List

FAKE_SERVERS: List[Dict] = [
    {
        "name": "CH#1",
        "country_code": "CH",
        "country_name": "Switzerland",
        "city": "Zurich",
        "load": 12,
    },
    {
        "name": "CH#2",
        "country_code": "CH",
        "country_name": "Switzerland",
        "city": "Geneva",
        "load": 34,
    },
    {
        "name": "DE#1",
        "country_code": "DE",
        "country_name": "Germany",
        "city": "Frankfurt",
        "load": 45,
    },
    {
        "name": "DE#2",
        "country_code": "DE",
        "country_name": "Germany",
        "city": "Berlin",
        "load": 22,
    },
    {
        "name": "NL#1",
        "country_code": "NL",
        "country_name": "Netherlands",
        "city": "Amsterdam",
        "load": 8,
    },
    {
        "name": "US#1",
        "country_code": "US",
        "country_name": "United States",
        "city": "New York",
        "load": 51,
    },
    {
        "name": "US#2",
        "country_code": "US",
        "country_name": "United States",
        "city": "Los Angeles",
        "load": 62,
    },
    {
        "name": "JP#1",
        "country_code": "JP",
        "country_name": "Japan",
        "city": "Tokyo",
        "load": 18,
    },
]


class _FakeState:
    """Stand-in for ``proton.vpn.connection.states.State``."""

    def __init__(self, name: str, reconnecting: bool = False, detail: str = None):
        self.name = name
        self.context = _FakeContext(reconnecting)
        self.detail = detail

    def __repr__(self):  # pragma: no cover - debugging aid
        return f"<FakeState {self.name}>"


class _FakeContext:
    def __init__(self, reconnection: bool):
        self.reconnection = reconnection


class FakeController:
    """Simulates the subset of the Controller API needed by the vertical slice."""

    def __init__(self, delay: float = 0.6):
        self._delay = delay
        self._executor = ThreadPoolExecutor(max_workers=2)
        self._subscribers: List[object] = []
        self._logged_in = False
        self._state = _FakeState("disconnected")
        self._user = "demo"

    def close(self):
        self._executor.shutdown(wait=False)

    # ---- Controller-like interface ----------------------------------------

    @property
    def user_logged_in(self) -> bool:
        return self._logged_in

    @property
    def account_name(self) -> str:
        return self._user

    @property
    def app_version(self) -> str:
        return "daemon-dev"

    @property
    def current_connection_status(self) -> _FakeState:
        return self._state

    def login(self, username: str, password: str) -> Future:
        def _login():
            time.sleep(self._delay)
            if not password:
                raise ValueError("Password cannot be empty")
            self._logged_in = True
            self._user = username
            return True

        return self._executor.submit(_login)

    def submit_2fa_code(self, code: str) -> Future:
        return self._executor.submit(lambda: True)

    def logout(self) -> Future:
        def _logout():
            time.sleep(self._delay / 2)
            self._logged_in = False
            self._set_state(_FakeState("disconnected"))
            return True

        return self._executor.submit(_logout)

    def connect_to_fastest_server(self) -> Future:
        return self._connect("connected", detail="Fastest")

    def connect_to_server(self, server_name: str = None) -> Future:
        return self._connect("connected", detail=server_name or "Server")

    def connect_to_country(self, country_code: str) -> Future:
        return self._connect("connected", detail=country_code or "Country")

    def get_servers(self) -> List[Dict]:
        return list(FAKE_SERVERS)

    def disconnect(self) -> Future:
        def _disconnect():
            self._set_state(_FakeState("disconnecting"))
            time.sleep(self._delay)
            self._set_state(_FakeState("disconnected"))
            return True

        return self._executor.submit(_disconnect)

    def register_connection_status_subscriber(self, subscriber) -> None:
        if subscriber not in self._subscribers:
            self._subscribers.append(subscriber)

    def unregister_connection_status_subscriber(self, subscriber) -> None:
        if subscriber in self._subscribers:
            self._subscribers.remove(subscriber)

    # ---- internals --------------------------------------------------------

    def _connect(self, final_state: str, detail: str = None) -> Future:
        def _do_connect():
            self._set_state(_FakeState("connecting", detail=detail))
            time.sleep(self._delay)
            self._set_state(_FakeState(final_state, detail=detail))
            return True

        return self._executor.submit(_do_connect)

    def _set_state(self, state: _FakeState) -> None:
        self._state = state
        for subscriber in list(self._subscribers):
            subscriber.connection_status_update(state)
