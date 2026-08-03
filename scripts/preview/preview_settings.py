#!/usr/bin/env python3
"""Settings UI preview — renders the real SettingsWindow with a mock controller
so CSS can be iterated visually (Ctrl+R to reload)."""
from __future__ import annotations

import sys
from concurrent.futures import Future
from pathlib import Path
from types import ModuleType
from unittest.mock import Mock

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
gi.require_version("Notify", "0.7")

from gi.repository import Gio, Gdk, GLib, Gtk

from proton.vpn.app.gtk.assets.style import STYLE_PATH
from proton.vpn.app.gtk.widgets.headerbar.menu.settings.settings_window import (
    SettingsWindow,
)
from proton.vpn.app.gtk.settings_watchers import SettingsWatchers
from proton.vpn.connection import states
from proton.vpn.connection.enum import KillSwitchSetting
from proton.vpn.app.gtk.controller import Controller
from proton.vpn.app.gtk.widgets.headerbar.menu.settings.feature_settings import (
    FeatureSettings,
)
from proton.vpn.app.gtk.widgets.headerbar.menu.settings.early_access import (
    EarlyAccessWidget,
)
from proton.vpn.app.gtk.widgets.headerbar.menu.settings.general_settings import (
    GeneralSettings,
)
from proton.vpn.app.gtk.widgets.vpn.serverlist.city_view.favorites import (
    FAVORITES_SETTING,
)

_providers = []


def apply_css():
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


def done_future(result=None):
    future = Future()
    future.set_result(result)
    return future


class SettingsMockController:
    def __init__(self):
        self.user_tier = 2
        self.user_logged_in = True
        self.connection_disconnected = True
        self.is_connection_active = False
        self.split_tunneling_available = False
        self._favorites = {"Japan"}
        self.settings_watchers = SettingsWatchers()
        self.executor = Mock()
        self.executor.submit = Mock(return_value=done_future())
        self._account_name = "user@proton.me"
        self._account_plan = "Plus"
        self._killswitch = 1
        self._protocol = "wireguard"
        self._dns_enabled = False
        self._dns_ip_list = []
        self._netshield = 0
        self._port_forwarding = False
        self._vpn_accelerator = False
        self._moderate_nat = False
        self._ipv6 = False
        self._anonymous_crash_reports = False
        self._connect_at_startup = None
        self._start_app_minimized = False
        self._tray_pinned_servers = ""
        self._packet_capture_dir = "/tmp"
        self._current_connection = Mock()
        self._current_connection.are_feature_updates_applied_when_active = False
        self._current_connection.start_packet_capture = Mock(
            return_value=done_future()
        )
        self._current_connection.stop_packet_capture = Mock(
            return_value=done_future()
        )
        self.reconnector = Mock()
        self.reconnector.enable = Mock()
        self.reconnector.disable = Mock()

    @property
    def account_name(self):
        return self._account_name

    @property
    def account_data(self):
        acct = Mock()
        acct.plan_title = self._account_plan
        return acct

    @property
    def current_connection(self):
        return self._current_connection

    def get_setting_attr(self, name):
        mapping = {
            FAVORITES_SETTING: sorted(self._favorites),
            "settings.features.netshield": self._netshield,
            "settings.features.port_forwarding": self._port_forwarding,
            "settings.features.vpn_accelerator": self._vpn_accelerator,
            "settings.features.moderate_nat": self._moderate_nat,
            "settings.ipv6": self._ipv6,
            "settings.anonymous_crash_reports": self._anonymous_crash_reports,
            "settings.killswitch": self._killswitch,
            "settings.protocol": self._protocol,
            "settings.packet_capture.directory_path": self._packet_capture_dir,
            "app_configuration.connect_at_app_startup": self._connect_at_startup,
            "app_configuration.start_app_minimized": self._start_app_minimized,
            "app_configuration.tray_pinned_servers": self._tray_pinned_servers,
            "settings.custom_dns.enabled": self._dns_enabled,
            "settings.custom_dns.ip_list": self._dns_ip_list,
        }
        return mapping.get(name, False)

    def save_setting_attr(self, name, value):
        return done_future()

    def get_settings(self):
        proto = Mock()
        proto.protocol = self._protocol
        proto.supports_packet_capture = lambda: True
        return Mock(protocol=proto)

    def get_available_protocols(self, group):
        return []

    def setting_attr_has_conflict(self, name, value):
        return None

    def register_connection_status_subscriber(self, sub):
        return None

    def unregister_connection_status_subscriber(self, sub):
        return None

    def run_subprocess(self, commands, check=False):
        return done_future()


class _EarlyAccessPatched(EarlyAccessWidget):
    def can_early_access_be_displayed(self):
        return False


class SettingsPreviewApp:
    def __init__(self):
        self._controller = SettingsMockController()
        self.window = SettingsWindow(self._controller)
        self.window.set_name("main-window")
        self.window.set_title("Proton VPN GTK — Settings Preview")
        self.window.set_default_size(620, 780)

        # Patch EarlyAccessWidget to skip subprocess calls in preview
        EarlyAccessWidget.can_early_access_be_displayed = (
            lambda self: False
        )
        # Patch packet capture visibility to show the row
        GeneralSettings._protocol_supports_packet_capture = (
            lambda self, protocol: True
        )

        self._add_keyboard_shortcuts()

    def _build_headerbar(self):
        return None

    def _add_keyboard_shortcuts(self):
        controller = Gtk.EventControllerKey()
        controller.connect("key-pressed", self._on_key_pressed)
        self.window.add_controller(controller)

    def _on_key_pressed(self, _controller, keyval, _keycode, _state):
        if keyval == Gdk.KEY_r and _state & Gdk.ModifierType.CONTROL_MASK:
            self._reload_css()
            return True
        return False

    def _reload_css(self):
        apply_css()


def _parse_args():
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


def main():
    args = _parse_args()
    apply_css()
    preview = SettingsPreviewApp()
    preview.window.present()

    if args.get("auto_shots"):
        _run_auto_shots(preview, args["auto_shots"], args.get("display") or ":0")
    elif args.get("geometry"):
        _dump_geometry(preview)
    else:
        GLib.MainLoop().run()


def _dump_geometry(preview):
    import time

    context = GLib.MainContext.default()
    deadline = time.time() + 2.0
    while time.time() < deadline:
        while context.pending():
            context.iteration(False)
        time.sleep(0.05)

    widget_names = [
        ("window", preview.window),
        ("settings-window", preview._settings_window),
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
    preview.window.close()


def _run_auto_shots(preview, out_dir, display):
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

    from gi.repository import GdkX11

    surface = preview.window.get_native().get_surface()
    xid = GdkX11.X11Surface.get_xid(surface)
    (out_dir / "xid.txt").write_text(str(xid))
    time.sleep(0.5)

    def capture(name):
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
        print(f"[settings-preview] captured {target}")

    capture("settings-default")
    preview.window.close()
    print("[settings-preview] auto-shots done")


if __name__ == "__main__":
    main()