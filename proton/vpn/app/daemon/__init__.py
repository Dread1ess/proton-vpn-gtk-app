"""
Proton VPN daemon: thin RPC layer over the Proton VPN Controller.

The daemon keeps all the existing Python backend logic (Controller,
VPNConnector, API, reconnector) untouched and exposes it to the Rust + Slint
GUI through a JSON-RPC 2.0 interface over a local unix socket.

Copyright (c) 2026 Proton AG

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

__version__ = "0.1.0"
