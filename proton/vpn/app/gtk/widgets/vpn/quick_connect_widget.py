"""
This module defines the Quick Connect widget.


Copyright (c) 2023 Proton AG

This file is part of Proton VPN.

Proton VPN is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

Proton VPN is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with ProtonVPN.  If not, see <https://www.gnu.org/licenses/>.
"""
from gi.repository import GLib
from proton.vpn.connection import states

from proton.vpn.app.gtk import Gtk
from proton.vpn.app.gtk.controller import Controller
from proton.vpn.app.gtk.utils.safe_signal_connect import safe_signal_connect
from proton.vpn import logging

logger = logging.getLogger(__name__)


class QuickConnectWidget(Gtk.Box):
    """Widget handling the "Quick Connect" functionality."""
    # CSS classes describing the power button visual state.
    POWER_BUTTON_CLASSES = ("power-off", "power-on", "power-busy", "power-error")

    def __init__(self, controller: Controller):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.set_name("quick-connect-widget")
        self._controller = controller
        self._connection_state: states.State = None

        self.connect_button = self._build_power_button()
        safe_signal_connect(
            self.connect_button,
            "clicked", self._on_connect_button_clicked)

        self.disconnect_button = self._build_power_button()
        safe_signal_connect(
            self.disconnect_button,
            "clicked", self._on_disconnect_button_clicked)

        # Keep a single sized placeholder for whichever power button is active,
        # so switching states does not change the widget height.
        self._power_stack = Gtk.Stack()
        self._power_stack.set_halign(Gtk.Align.CENTER)
        self._power_stack.set_valign(Gtk.Align.CENTER)
        self._power_stack.add_named(self.connect_button, "connect")
        self._power_stack.add_named(self.disconnect_button, "disconnect")

        self.action_label = Gtk.Label(label="Connect")
        self.action_label.set_name("quick-connect-action-label")
        self.action_label.add_css_class("body-3")
        self.action_label.set_halign(Gtk.Align.CENTER)

        self.append(self._power_stack)
        self.append(self.action_label)

    def _build_power_button(self) -> Gtk.Button:
        """Builds a big circular power button with a symbolic power icon.

        The button content is a stack with two pages: the power icon and a
        spinner, the latter shown while a connection is in progress.
        """
        button = Gtk.Button()
        button.add_css_class("power-button")
        button.add_css_class("power-off")
        button.set_halign(Gtk.Align.CENTER)
        button.set_valign(Gtk.Align.CENTER)
        button.set_size_request(136, 136)

        content = Gtk.Stack()
        content.set_hhomogeneous(True)
        content.set_vhomogeneous(True)

        icon = Gtk.Image.new_from_icon_name("power-symbolic")
        icon.set_pixel_size(48)
        content.add_named(icon, "icon")

        spinner = Gtk.Spinner()
        spinner.set_size_request(48, 48)
        content.add_named(spinner, "spinner")

        button.set_child(content)
        button.content_stack = content
        button.spinner = spinner
        return button

    @property
    def connection_state(self):
        """Returns the current connection state."""
        return self._connection_state

    @connection_state.setter
    def connection_state(self, connection_state: states.State):
        """Sets the current connection state, updating the UI accordingly."""
        # pylint: disable=duplicate-code
        self._connection_state = connection_state

        # Update the UI according to the connection state.
        if isinstance(connection_state, states.Disconnected) \
                and not connection_state.context.reconnection:
            self._on_connection_state_disconnected()
        elif isinstance(connection_state, states.Connecting):
            self._on_connection_state_connecting()
        elif isinstance(connection_state, states.Connected):
            self._on_connection_state_connected()
        elif isinstance(connection_state, states.Disconnecting):
            self._on_connection_state_disconnecting()
        elif isinstance(connection_state, states.Error):
            self._on_connection_state_error()

    def connection_status_update(self, connection_state):
        """This method is called by VPNWidget whenever the VPN connection status changes."""
        self.connection_state = connection_state

    def _on_connection_state_disconnected(self):
        self._set_power_state("connect", "icon", "power-off", "Connect")

    def _on_connection_state_connecting(self):
        self._set_power_state("disconnect", "spinner", "power-busy", "Cancel Connection")

    def _on_connection_state_connected(self):
        self._set_power_state("disconnect", "icon", "power-on", "Disconnect")

    def _on_connection_state_disconnecting(self):
        self._set_power_state("disconnect", "spinner", "power-busy", "Disconnecting...")

    def _on_connection_state_error(self):
        self._set_power_state("disconnect", "icon", "power-error", "Cancel Connection")

    def _set_power_state(
            self, power_button_name: str, content_page: str, css_class: str, label: str
    ):
        """Updates which power button is shown and how it is styled."""
        self._power_stack.set_visible_child_name(power_button_name)
        active_button = self.connect_button \
            if power_button_name == "connect" else self.disconnect_button

        active_button.content_stack.set_visible_child_name(content_page)
        if content_page == "spinner":
            active_button.spinner.start()
        else:
            active_button.spinner.stop()

        for cls in self.POWER_BUTTON_CLASSES:
            if cls == css_class:
                active_button.add_css_class(cls)
            else:
                active_button.remove_css_class(cls)

        self.action_label.set_label(label)

    def _on_connect_button_clicked(self, _):
        logger.info("Connect to fastest server", category="ui.tray", event="connect")
        future = self._controller.connect_to_fastest_server()
        future.add_done_callback(lambda f: GLib.idle_add(f.result))  # bubble up exceptions if any.

    def _on_disconnect_button_clicked(self, _):
        logger.info("Disconnect from VPN", category="ui", event="disconnect")
        future = self._controller.disconnect()
        future.add_done_callback(lambda f: GLib.idle_add(f.result))  # bubble up exceptions if any.
