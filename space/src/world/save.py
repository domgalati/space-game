"""One save file per run: the player (ship, cargo, location) and the world (flags, people,
prices, news), as YAML.

What's in flight isn't kept: other ships, wrecks and sensor contacts start fresh on load,
so the cleanest moment to save is while docked, which is when the game autosaves.
"""
import os

import yaml

from entities.player import Player
from util.config import resolve_game_path
from world.world_state import WorldState

SAVE_PATH = "space/saves/save.yaml"
VERSION = 1


class SaveError(Exception):
    """A save that can't be read: missing, damaged, or from an incompatible version."""


def save_path(path=None):
    return path or resolve_game_path(SAVE_PATH)


def has_save(path=None):
    return os.path.exists(save_path(path))


def save_game(player, world_state, path=None):
    """Write the run to `path` (default SAVE_PATH). Writes a temp file first, so a crash
    mid-save leaves the previous save intact. Returns the path written."""
    path = save_path(path)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    data = {"version": VERSION, "player": player.to_dict(), "world": world_state.to_dict()}
    temp = f"{path}.tmp"
    with open(temp, "w", encoding="utf-8") as file:
        yaml.safe_dump(data, file, sort_keys=False, allow_unicode=True)
    os.replace(temp, path)
    return path


def load_game(path=None):
    """(player, world_state) from `path` (default SAVE_PATH). Raises SaveError if it can't."""
    path = save_path(path)
    try:
        with open(path, "r", encoding="utf-8") as file:
            data = yaml.safe_load(file)
    except (OSError, yaml.YAMLError) as exc:
        raise SaveError(f"Can't read {path}: {exc}") from exc
    if not isinstance(data, dict) or data.get("version") != VERSION:
        version = data.get("version") if isinstance(data, dict) else None
        raise SaveError(f"{path} is save version {version}; this game reads version {VERSION}")
    return Player.from_dict(data.get("player") or {}), WorldState(data.get("world") or {})
