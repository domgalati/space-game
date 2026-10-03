"""Hand-authored characters, defined in space/characters/<id>.yaml.

A map places one with an object named ``character:<id>`` in its "NPC Posts" layer.
"""
from pathlib import Path

import yaml

from entities.npcs.portrait import roll_appearance
from util.config import resolve_game_path

CHARACTER_DIR = "space/characters"
POST_PREFIX = "character:"
REQUIRED = ("id", "name", "job", "guild", "dialogue")


def character_path(char_id):
    return Path(resolve_game_path(f"{CHARACTER_DIR}/{char_id}.yaml"))


def load_character(char_id):
    path = character_path(char_id)
    with open(path, "r", encoding="utf-8") as file:
        definition = yaml.safe_load(file) or {}
    missing = [key for key in REQUIRED if not definition.get(key)]
    if missing:
        raise ValueError(f"{path.name} is missing {', '.join(missing)}")
    if definition["id"] != char_id:
        raise ValueError(f"{path.name} has id {definition['id']!r}; it must match the file name")
    return definition


def character_record(definition):
    """The same record shape the roster uses, so one builder makes both kinds of NPC."""
    npc_id = f"{POST_PREFIX}{definition['id']}"
    first, _, last = definition["name"].partition(" ")
    species = definition.get("species", "human")
    return {
        "id": npc_id,
        "firstname": first,
        "lastname": last,
        "job": definition["job"],
        "guild": definition["guild"],
        "species": species,
        "hobbies": list(definition.get("hobbies", [])),
        "portrait": roll_appearance(
            npc_id, species, definition["job"], definition["guild"], fixed=definition.get("portrait")
        ),
        "dialogue": definition["dialogue"],
        "start_node": definition.get("start_node", "Start"),
        "sprite": definition.get("sprite"),
        "mood": definition.get("mood"),
    }
