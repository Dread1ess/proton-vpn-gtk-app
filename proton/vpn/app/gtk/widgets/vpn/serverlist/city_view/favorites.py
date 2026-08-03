"""
Favorites (starred countries/servers) helpers.

Favorites are persisted in the app configuration under
``app_configuration.favorite_servers`` as a list of item names
(country names or server names such as ``NL#2``).


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
from __future__ import annotations

from typing import Set

FAVORITES_SETTING = "app_configuration.favorite_servers"


def load_favorites(controller) -> Set[str]:
    """Returns the set of favorited item names, or an empty set on failure."""
    try:
        favorites = controller.get_setting_attr(FAVORITES_SETTING)
    except (AttributeError, NotImplementedError, ValueError):
        return set()

    if isinstance(favorites, (list, tuple, set)):
        return set(favorites)

    return set()


def toggle_favorite(controller, name: str) -> bool:
    """Toggles the favorite state of an item and persists it.

    Returns the new favorite state (True if the item is now a favorite).
    """
    favorites = load_favorites(controller)
    if name in favorites:
        favorites.discard(name)
        is_favorite = False
    else:
        favorites.add(name)
        is_favorite = True

    controller.save_setting_attr(FAVORITES_SETTING, sorted(favorites))
    return is_favorite
