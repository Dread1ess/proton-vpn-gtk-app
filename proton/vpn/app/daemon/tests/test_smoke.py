"""
End-to-end smoke test for the daemon IPC: spawns the daemon in mock mode,
exercises handshake/login/connect/disconnect/status over the unix socket,
then shuts it down.

Run from the repo root:
    python3 -m proton.vpn.app.daemon.tests.test_smoke
"""
from __future__ import annotations

import asyncio
import json
import os
import subprocess
import sys
import tempfile
import time

REPO_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "..")
)


class RpcClient:
    """Minimal JSON-RPC 2.0 client over a unix socket (for tests).

    A single reader task routes messages: responses resolve the pending
    request future by id, notifications are queued for ``read_event``.
    This mirrors the real Rust client's dispatcher.
    """

    def __init__(self, path: str):
        self._path = path
        self._reader = None
        self._writer = None
        self._next_id = 0
        self._pending: dict = {}
        self._notifications: asyncio.Queue = asyncio.Queue()
        self._reader_task = None

    async def connect(self) -> None:
        self._reader, self._writer = await asyncio.open_unix_connection(self._path)
        self._reader_task = asyncio.create_task(self._pump())

    async def _pump(self) -> None:
        try:
            while True:
                line = await self._reader.readline()
                if not line:
                    break
                message = json.loads(line)
                if "method" in message and "id" not in message:
                    await self._notifications.put(message)
                elif message.get("id") is not None:
                    future = self._pending.pop(message["id"], None)
                    if future is not None and not future.done():
                        future.set_result(message)
        except asyncio.CancelledError:
            raise

    async def request(self, method: str, params=None) -> dict:
        self._next_id += 1
        request_id = self._next_id
        payload = {"jsonrpc": "2.0", "id": request_id, "method": method}
        if params is not None:
            payload["params"] = params
        future = asyncio.get_running_loop().create_future()
        self._pending[request_id] = future
        self._writer.write((json.dumps(payload) + "\n").encode())
        await self._writer.drain()
        return await asyncio.wait_for(future, timeout=15)

    async def read_event(self, timeout: float = 5.0) -> dict:
        """Reads the next server notification."""
        return await asyncio.wait_for(self._notifications.get(), timeout=timeout)

    async def close(self) -> None:
        if self._reader_task is not None:
            self._reader_task.cancel()
        self._writer.close()
        await self._writer.wait_closed()


async def run_test() -> None:
    tmp = tempfile.mkdtemp(prefix="protonvpn-daemon-test-")
    socket_path = os.path.join(tmp, "daemon.sock")

    daemon = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "proton.vpn.app.daemon",
            "--mock",
            "--socket",
            socket_path,
        ],
        cwd=REPO_ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    try:
        deadline = time.time() + 15
        while not os.path.exists(socket_path) and time.time() < deadline:
            await asyncio.sleep(0.1)
        if not os.path.exists(socket_path):
            raise AssertionError("Daemon did not create the socket in time")

        client = RpcClient(socket_path)
        await client.connect()

        # Handshake.
        hs = await client.request("handshake", {"protocol_version": 1})
        assert hs["result"]["protocol_version"] == 1, hs
        print("OK handshake")

        # Login (empty password -> error).
        bad = await client.request("login", {"username": "u", "password": ""})
        assert "error" in bad, bad
        print("OK login rejects empty password")

        # Login.
        login = await client.request("login", {"username": "alice", "password": "secret"})
        assert login["result"]["logged_in"] is True, login
        print("OK login")

        # Status before connect.
        status = await client.request("get_status")
        assert status["result"]["state"] == "disconnected", status
        print("OK status disconnected")

        # Connect -> expect push events connecting, then connected.
        connect_task = asyncio.create_task(
            client.request("connect_to_fastest_server")
        )
        events = []
        while len(events) < 2:
            event = await client.read_event()
            if event.get("method") == "connection_status":
                events.append(event["params"]["state"])
        assert events[0] == "connecting", events
        assert events[1] == "connected", events
        connect_result = await connect_task
        assert connect_result["result"]["state"] == "connected", connect_result
        print("OK connect + push events:", events)

        # Disconnect -> push events disconnecting, disconnected.
        disconnect_task = asyncio.create_task(client.request("disconnect"))
        events = []
        while len(events) < 2:
            event = await client.read_event()
            if event.get("method") == "connection_status":
                events.append(event["params"]["state"])
        assert events[0] == "disconnecting", events
        assert events[1] == "disconnected", events
        await disconnect_task
        print("OK disconnect + push events:", events)

        # Unknown method.
        unknown = await client.request("does_not_exist")
        assert unknown["error"]["code"] == -32601, unknown
        print("OK unknown method rejected")

        await client.close()
        print("ALL TESTS PASSED")
    finally:
        daemon.terminate()
        try:
            daemon.wait(timeout=10)
        except subprocess.TimeoutExpired:
            daemon.kill()
        if daemon.returncode not in (0, -15, None):
            print("--- daemon stderr ---", file=sys.stderr)
            print(daemon.stderr.read().decode(), file=sys.stderr)


if __name__ == "__main__":
    asyncio.run(run_test())
