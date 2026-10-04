"""Every star system and the bodies in it, by stable id, read from space/star_systems/*.json.

A body's id is "<system>/<body>", e.g. "sol/terramonta". Game state (markets, rosters, nav
charts, news) is keyed by id so names can change and two systems can share one; players
only ever see names. Reading the atlas loads no art, so it is safe anywhere.
"""
import json
from functools import lru_cache
from pathlib import Path

from util.config import resolve_game_path

SYSTEM_DIR = "space/star_systems"


def body_id(system_id, local_id):
    return f"{system_id}/{local_id}"


def system_of(place):
    """The system id of a body id, or None for a key that isn't one."""
    system, sep, _ = str(place).partition("/")
    return system if sep else None


@lru_cache(maxsize=None)
def _bodies():
    bodies = {}
    for path in sorted(Path(resolve_game_path(SYSTEM_DIR)).glob("*.json")):
        with open(path, "r", encoding="utf-8") as file:
            data = json.load(file)
        system = data.get("id")
        if not system:
            continue
        for entry in [*data.get("planets", []), *data.get("objects", [])]:
            place = body_id(system, entry["id"])
            bodies[place] = {"id": place, "name": entry["name"], "system": system}
    return bodies


def body(place):
    """{id, name, system} for a body id, or None."""
    return _bodies().get(place)


def place_name(place):
    """What the player calls a place. Keys that aren't body ids are shown as they are."""
    entry = body(place)
    return entry["name"] if entry else place
