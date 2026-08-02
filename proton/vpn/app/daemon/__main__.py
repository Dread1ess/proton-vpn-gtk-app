"""
Daemon entry point.

Usage:
    python -m proton.vpn.app.daemon [--mock] [--socket PATH]

``--mock`` runs the daemon against an in-memory fake controller so the GUI
vertical slice can be developed and demoed without the Proton backend.

Without ``--mock`` the daemon builds the real GTK ``Controller`` (which
requires the Proton backend packages installed from the internal registry).

Copyright (c) 2026 Proton AG
"""
from __future__ import annotations

import argparse
import asyncio
import logging
import os
import sys

from proton.vpn.app.daemon import protocol
from proton.vpn.app.daemon.server import DaemonServer

logger = logging.getLogger(__name__)


def default_socket_path() -> str:
    env_socket = os.environ.get(protocol.SOCKET_ENV_VAR)
    if env_socket:
        return env_socket
    runtime_dir = os.environ.get("XDG_RUNTIME_DIR") or "/tmp"
    return os.path.join(runtime_dir, protocol.DEFAULT_SOCKET_NAME)


def build_real_controller():
    """Builds the production controller (GTK app Controller)."""
    try:
        from proton.vpn.app.gtk.controller import Controller
        from proton.vpn.app.gtk.utils.exception_handler import ExceptionHandler
        from proton.vpn.app.gtk.utils.executor import AsyncExecutor
    except ModuleNotFoundError as excp:
        print(
            "Proton VPN backend packages are not installed. "
            "Install proton-vpn-api-core and friends from the internal "
            "registry, or run the daemon with --mock for development.",
            file=sys.stderr,
        )
        raise SystemExit(f"Missing dependency: {excp.name}") from excp

    executor = AsyncExecutor()
    exception_handler = ExceptionHandler()
    executor.start()
    try:
        controller = Controller.get(executor, exception_handler)
    except Exception:
        executor.stop()
        raise
    return controller


def configure_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Proton VPN daemon")
    parser.add_argument("--mock", action="store_true", help="Use fake controller")
    parser.add_argument(
        "--socket", default=default_socket_path(), help="Unix socket path"
    )
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()

    configure_logging(args.verbose)

    if args.mock:
        from proton.vpn.app.daemon.fake_controller import FakeController

        controller = FakeController()
        logger.info("Using mock controller")
    else:
        controller = build_real_controller()

    server = DaemonServer(controller, args.socket)

    async def run():
        try:
            await server.serve_forever()
        except asyncio.CancelledError:
            pass
        finally:
            if getattr(controller, "close", None):
                controller.close()

    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
