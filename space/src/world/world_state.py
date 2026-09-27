"""Persistent world facts: story flags, per-NPC memory, and each location's residents.

Written to a generated file that is never committed; a real save-slot system comes later.
"""
import os

import yaml

from util.config import resolve_game_path

SAVE_PATH = "space/saves/world_state.yaml"
VERSION = 1


class WorldState:
    def __init__(self, path=None, data=None):
        self.path = path or resolve_game_path(SAVE_PATH)
        data = data or {}
        self.globals = data.get("globals") or {}
        self.npcs = data.get("npcs") or {}  # npc_id -> {mood, vars, visited}
        self.rosters = data.get("rosters") or {}  # location -> [npc record]

    @classmethod
    def load(cls, path=None):
        path = path or resolve_game_path(SAVE_PATH)
        data = None
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as file:
                data = yaml.safe_load(file)
        return cls(path, data)

    def npc_state(self, npc_id, default_mood=0):
        state = self.npcs.get(npc_id)
        if state is None:
            state = {"mood": default_mood, "vars": {}, "visited": {}}
            self.npcs[npc_id] = state
        return state

    def to_dict(self):
        return {
            "version": VERSION,
            "globals": self.globals,
            "npcs": self.npcs,
            "rosters": self.rosters,
        }

    def save(self):
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        temp = f"{self.path}.tmp"
        with open(temp, "w", encoding="utf-8") as file:
            yaml.safe_dump(self.to_dict(), file, sort_keys=False, allow_unicode=True)
        os.replace(temp, self.path)
