"""Every item in the game, by stable id, read from space/items.yaml.

Inventories, markets, saves and events store ids ("raw-minerals"); players see names
("Raw Minerals"). Text a person typed or wrote in a script can name an item either way:
find_item turns it into an id. Ids the registry doesn't know are shown as they are.
"""
from functools import lru_cache

import yaml

from util.config import resolve_game_path

ITEMS_PATH = "space/items.yaml"
CATEGORIES = ("cargo", "quest", "gear")


@lru_cache(maxsize=None)
def _items():
    with open(resolve_game_path(ITEMS_PATH), "r", encoding="utf-8") as file:
        items = yaml.safe_load(file) or {}
    for item_id, entry in items.items():
        if entry.get("category") not in CATEGORIES:
            raise ValueError(f"items.yaml: {item_id} needs a category, one of {', '.join(CATEGORIES)}")
        entry["id"] = item_id
    return items


def item(item_id):
    """{id, name, category, ...} for an item id, or None."""
    return _items().get(item_id)


def item_name(item_id):
    """What the player calls an item. Ids the registry doesn't know are shown as they are."""
    entry = item(item_id)
    return entry["name"] if entry else item_id


def find_item(text):
    """The id for `text`, which may be an id or a name in any case. Unknown text comes back as is."""
    if text in _items():
        return text
    folded = str(text).lower()
    for item_id, entry in _items().items():
        if entry["name"].lower() == folded:
            return item_id
    return text
