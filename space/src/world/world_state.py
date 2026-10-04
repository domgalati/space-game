"""In-session world facts: story flags, per-NPC memory, residents, markets, and news.

Load/save helpers remain for tests and a future save-slot system. The game currently
starts a fresh ``WorldState()`` every run and does not write to disk.

Places are keyed by body id ("sol/terramonta", see world.atlas), never by display name.
"""
import os

import yaml

from util.config import resolve_game_path

SAVE_PATH = "space/saves/world_state.yaml"
VERSION = 2  # 2: rosters and news keyed by body id instead of planet name


class WorldState:
    def __init__(self, path=None, data=None):
        self.path = path or resolve_game_path(SAVE_PATH)
        data = data or {}
        self.globals = data.get("globals") or {}
        self.npcs = data.get("npcs") or {}  # npc_id -> {mood, vars, visited}
        self.rosters = data.get("rosters") or {}  # location -> [npc record]
        self.news = data.get("news") or {}  # see util.economy.news_feed
        self.markets = None  # live economy data for this run; see markets_data()

    def markets_data(self):
        """Session market book. Loaded once from the base yaml, then mutated in place."""
        if self.markets is None:
            from util.economy.economy import load_market_data
            self.markets = load_market_data()
        return self.markets

    @classmethod
    def load(cls, path=None):
        """Reload from disk. Unused by the game until save slots exist."""
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
            "news": self.news,
        }

    def save(self):
        """Write to disk. The game does not call this until save slots exist."""
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        temp = f"{self.path}.tmp"
        with open(temp, "w", encoding="utf-8") as file:
            yaml.safe_dump(self.to_dict(), file, sort_keys=False, allow_unicode=True)
        os.replace(temp, self.path)
