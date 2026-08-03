#!/usr/bin/env python3
"""
Standalone UI preview harness for the Proton VPN GTK app.

It renders the real VPN widget (quick connect, connection status, search and
server list) with fake data and a mocked controller, so you can iterate on the
UI/CSS without installing the private backend packages.

Usage:
    python3 scripts/preview/preview.py

Controls:
    Click the buttons in the top bar to switch connection state / plan tier.
    Ctrl+R  reload the CSS files without restarting the preview.
"""
from __future__ import annotations

import sys
from concurrent.futures import Future
from pathlib import Path
from types import ModuleType
from unittest.mock import Mock

REPO_ROOT = Path(__file__).resolve().parents[2]
STUBS_PATH = Path(__file__).resolve().parent / "stubs"

sys.path.insert(0, str(STUBS_PATH))
sys.path.insert(0, str(REPO_ROOT))

# The real split-tunneling settings module pulls in the entire settings tree
# (and the real Controller), which is too heavy for the preview. We only need
# the constant that the connection status widget imports.
_SPLIT_TUNNELING_MODULE_NAME = (
    "proton.vpn.app.gtk.widgets.headerbar.menu.settings."
    "split_tunneling.split_tunneling"
)
_split_tunneling_stub = ModuleType(_SPLIT_TUNNELING_MODULE_NAME)
_split_tunneling_stub.SPLIT_TUNNELING_TOGGLE_SETTING_NAME = \
    "settings.features.split_tunneling.enabled"
sys.modules[_SPLIT_TUNNELING_MODULE_NAME] = _split_tunneling_stub

# The real Controller drags in the whole private backend (proton-vpn-core).
# The widgets only use it as a type annotation, so a stub class is enough.
_CONTROLLER_MODULE_NAME = "proton.vpn.app.gtk.controller"
_controller_stub = ModuleType(_CONTROLLER_MODULE_NAME)


class Controller:  # pylint: disable=too-few-public-methods
    """Stub controller type used only for annotations in the preview."""


_controller_stub.Controller = Controller
sys.modules[_CONTROLLER_MODULE_NAME] = _controller_stub

import gi  # noqa: E402

gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
gi.require_version("Notify", "0.7")

from gi.repository import Gdk, GLib, Gtk  # noqa: E402

from proton.vpn import logging  # noqa: E402

logging.config(filename="vpn-preview")

from proton.vpn.app.gtk import Gtk as _Gtk  # noqa: E402  (ensures app init runs)
from proton.vpn.app.gtk.assets.style import STYLE_PATH  # noqa: E402
from proton.vpn.app.gtk.widgets.vpn.vpn_widget import VPNWidget  # noqa: E402
from proton.vpn.app.gtk.widgets.vpn.serverlist.city_view.favorites import FAVORITES_SETTING  # noqa: E402
from proton.vpn.connection import events, states  # noqa: E402
from proton.vpn.connection.states import ConnectionContext  # noqa: E402
from proton.vpn.session.servers import TierEnum  # noqa: E402

from fake_data import build_fake_server_list  # noqa: E402

_providers = []


def apply_css():
    """(Re)applies the app stylesheet to the default display."""
    display = Gdk.Display.get_default()
    for provider in _providers:
        Gtk.StyleContext.remove_provider_for_display(display, provider)
    _providers.clear()

    provider = Gtk.CssProvider()
    provider.load_from_path(str(STYLE_PATH / "main.css"))
    _providers.append(provider)
    Gtk.StyleContext.add_provider_for_display(
        display, provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
    )


def done_future(result=None) -> Future:
    """Returns an already-completed concurrent Future."""
    future = Future()
    future.set_result(result)
    return future


class FakeConnection:
    """Minimal stand-in for a live VPN connection."""

    def __init__(self, server_name: str):
        self.server_name = server_name


class MockController:
    """Mock of the app Controller exposing only what the widgets use."""

    def __init__(self, server_list):
        self._server_list = server_list
        self.user_tier = int(TierEnum.PLUS)
        self.user_logged_in = True
        self.reconnector = Mock()
        self.reconnector.enable = Mock()
        self.reconnector.disable = Mock()
        self._favorites = {"Japan"}

    @property
    def server_list(self):
        return self._server_list

    @property
    def current_connection_status(self):
        return states.Disconnected(
            context=ConnectionContext(connection=None, reconnection=False)
        )

    def register_connection_status_subscriber(self, _subscriber):
        return None

    def unregister_connection_status_subscriber(self, _subscriber):
        return None

    def enable_refresher(self, _callback):
        return None

    def disable_refresher(self):
        return None

    def set_server_list_updated_callback(self, _callback):
        return None

    def set_server_loads_updated_callback(self, _callback):
        return None

    def get_setting_attr(self, name):
        if name == FAVORITES_SETTING:
            return sorted(self._favorites)
        return False

    def save_setting_attr(self, name, value):
        if name == FAVORITES_SETTING:
            self._favorites = set(value)
        return done_future()

    def connect_to_fastest_server(self):
        return done_future()

    def connect_to_server(self, _name=None):
        return done_future()

    def disconnect(self):
        return done_future()


class PreviewApp:
    """Builds and drives the preview window."""

    def __init__(self, controller: MockController, vpn_widget: VPNWidget):
        self._controller = controller
        self._vpn_widget = vpn_widget
        self._state_idx = 0
        self._free_tier = False

        self.window = Gtk.Window()
        self.window.set_title("Proton VPN GTK — UI preview")
        # Note: the top debug control bar (~696px wide) sets the preview
        # window's minimum width; the real app has no such controls.
        self.window.set_default_size(720, 860)
        self.window.get_settings().props.gtk_application_prefer_dark_theme = True

        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        outer.append(self._build_controls())
        self._vpn_widget.set_vexpand(True)
        self._vpn_widget.server_list_widget.set_vexpand(True)
        outer.append(self._vpn_widget)

        self.window.set_child(outer)
        self._add_keyboard_shortcuts()

    def _build_controls(self) -> Gtk.Box:
        controls = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        controls.set_margin_top(6)
        controls.set_margin_bottom(6)
        controls.set_margin_start(6)
        controls.set_margin_end(6)

        def state_button(label, index):
            button = Gtk.Button(label=label)
            button.connect(
                "clicked", lambda _btn, idx=index: self._set_state(idx)
            )
            controls.append(button)

        state_button("Unprotected", 0)
        state_button("Connecting", 1)
        state_button("Protected", 2)
        state_button("Error", 3)

        tier_button = Gtk.Button(label="Free/Paid")
        tier_button.connect("clicked", lambda _btn: self._toggle_tier())
        controls.append(tier_button)

        reload_button = Gtk.Button(label="Reload")
        reload_button.connect("clicked", lambda _btn: self._reload_css())
        controls.append(reload_button)

        self._state_label = Gtk.Label(label="")
        self._state_label.set_margin_start(12)
        self._state_label.set_max_width_chars(18)
        self._state_label.set_ellipsize(0)
        self._state_label.add_css_class("dim-label")
        controls.append(self._state_label)

        return controls

    def _add_keyboard_shortcuts(self):
        controller = Gtk.EventControllerKey()
        controller.connect("key-pressed", self._on_key_pressed)
        self.window.add_controller(controller)

    def _on_key_pressed(self, _controller, keyval, _keycode, _state):
        if keyval == Gdk.KEY_r and _state & Gdk.ModifierType.CONTROL_MASK:
            self._reload_css()
            return True
        if keyval == Gdk.KEY_1:
            self._set_state(0)
            return True
        if keyval == Gdk.KEY_2:
            self._set_state(1)
            return True
        if keyval == Gdk.KEY_3:
            self._set_state(2)
            return True
        if keyval == Gdk.KEY_4:
            self._set_state(3)
            return True
        return False

    def _set_state(self, idx: int):
        self._state_idx = idx
        if idx == 0:
            state = states.Disconnected(
                context=ConnectionContext(connection=None, reconnection=False)
            )
            label = "Disconnected"
        elif idx == 1:
            state = states.Connecting(
                context=ConnectionContext(
                    connection=FakeConnection("NL#2"), reconnection=False
                )
            )
            label = "Connecting NL#2"
        elif idx == 2:
            state = states.Connected(
                context=ConnectionContext(
                    connection=FakeConnection("NL#2"), reconnection=False
                )
            )
            label = "Protected NL#2"
        else:
            state = states.Error(
                context=ConnectionContext(
                    connection=FakeConnection("NL#2"),
                    event=events.TunnelSetupFailed(),
                )
            )
            label = "Error"
        self._state_label.set_text(label)
        self._vpn_widget.status_update(state)

    def _toggle_tier(self):
        self._free_tier = not self._free_tier
        self._controller.user_tier = int(
            TierEnum.FREE if self._free_tier else TierEnum.PLUS
        )
        self._vpn_widget.server_list_widget.display(
            self._controller.user_tier, self._controller.server_list
        )
        self._set_state(0)

    def _reload_css(self):
        apply_css()


def main():
    args = _parse_args()

    server_list = build_fake_server_list()
    controller = MockController(server_list)
    vpn_widget = VPNWidget(
        controller=controller,
        main_window=Mock(add_keyboard_shortcut=Mock()),
        notifications=Mock(),
    )
    vpn_widget.display(
        user_tier=controller.user_tier, server_list=controller.server_list
    )

    apply_css()
    preview = PreviewApp(controller, vpn_widget)
    preview._set_state(0)
    preview.window.present()

    if args.get("auto_shots"):
        _run_auto_shots(
            preview, args["auto_shots"], args.get("display") or ":0"
        )
    elif args.get("geometry"):
        _dump_geometry(preview)
    else:
        GLib.MainLoop().run()


def _dump_geometry(preview: "PreviewApp"):
    """Presents the preview, prints the allocation of key widgets, then exits."""
    import time

    context = GLib.MainContext.default()
    deadline = time.time() + 2.0
    while time.time() < deadline:
        while context.pending():
            context.iteration(False)
        time.sleep(0.05)

    widget_names = [
        ("window", preview.window),
        ("vpn-widget", preview._vpn_widget),
        ("connection-status", preview._vpn_widget.connection_status_widget),
        ("quick-connect", preview._vpn_widget.quick_connect_widget),
        ("connect-button", preview._vpn_widget.quick_connect_widget.connect_button),
        ("connect-action-label", preview._vpn_widget.quick_connect_widget.action_label),
        ("search-entry", preview._vpn_widget.search_widget),
        ("server-list", preview._vpn_widget.server_list_widget),
    ]
    for label, widget in widget_names:
        if widget is None:
            continue
        alloc = widget.get_allocation()
        natural_width, natural_height = widget.get_preferred_size()
        print(
            f"GEOM {label}: alloc=({alloc.x},{alloc.y} {alloc.width}x{alloc.height}) "
            f"natural=({natural_width.width}x{natural_height.height})"
        )

    # Row info: how many countries are displayed and their widths
    server_list = preview._vpn_widget.server_list_widget
    rows = server_list.country_rows
    print(f"GEOM countries: {len(rows)}")
    if rows:
        row_alloc = rows[0].get_allocation()
        print(
            f"GEOM first country row: ({row_alloc.width}x{row_alloc.height}) "
            f"label={rows[0].country_name}"
        )

    preview.window.close()


def _parse_args() -> dict:
    """Parses lightweight CLI args (no argparse needed for this harness)."""
    result = {}
    argv = sys.argv[1:]
    if "--auto-shots" in argv:
        index = argv.index("--auto-shots")
        result["auto_shots"] = argv[index + 1] if index + 1 < len(argv) else "."
    if "--display" in argv:
        index = argv.index("--display")
        result["display"] = argv[index + 1] if index + 1 < len(argv) else ":0"
    result["geometry"] = "--geometry" in argv
    return result


def _run_auto_shots(preview: "PreviewApp", out_dir: str, display: str):
    """Presents the preview, captures each connection state with ImageMagick
    ``import`` and saves the PNGs into ``out_dir``."""
    import os
    import subprocess
    import time

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    context = GLib.MainContext.default()
    for _ in range(600):
        while context.pending():
            context.iteration(False)
        if preview.window.get_realized():
            break

    from gi.repository import GdkX11  # pylint: disable=import-outside-toplevel

    surface = preview.window.get_native().get_surface()
    xid = GdkX11.X11Surface.get_xid(surface)
    (out_dir / "xid.txt").write_text(str(xid))
    time.sleep(0.5)

    def capture(name: str):
        # Give GTK a real frame to paint the current state before grabbing the
        # X window, otherwise the snapshot can show a stale frame.
        preview.window.queue_draw()
        end = time.time() + 1.0
        while time.time() < end:
            while context.pending():
                context.iteration(False)
            time.sleep(0.03)
        target = str(out_dir / f"{name}.png")
        subprocess.run(
            ["import", "-window", hex(xid), target],
            env={**os.environ, "DISPLAY": display},
            check=False,
        )
        print(f"[preview] captured {target}")

    capture("state-unprotected")
    for name, idx in (("connecting", 1), ("protected", 2), ("error", 3)):
        preview._set_state(idx)
        capture(f"state-{name}")

    if not preview._free_tier:
        preview._toggle_tier()
        capture("state-free-tier")

    preview.window.close()
    print("[preview] auto-shots done")


if __name__ == "__main__":
    main()
