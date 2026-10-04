"""World facts for a run: story flags, per-NPC memory, residents, markets, and news.

Saved with the player by world.save. Places are keyed by body id ("sol/terramonta", see
world.atlas), never by display name. ``events`` announces what happens; it isn't saved.
"""
from world.events import Events


class WorldState:
    def __init__(self, data=None):
        data = data or {}
        self.events = Events()
        self.globals = data.get("globals") or {}
        self.npcs = data.get("npcs") or {}  # npc_id -> {mood, vars, visited}
        self.rosters = data.get("rosters") or {}  # location -> [npc record]
        self.news = data.get("news") or {}  # see util.economy.news_feed
        self.markets = None  # live economy data for this run; see markets_data()
        self._saved_prices = data.get("prices") or {}  # place -> good -> price, from a save

    def markets_data(self):
        """The run's market book: the base yaml with any saved prices, then mutated in place."""
        if self.markets is None:
            from util.economy.economy import load_market_data
            self.markets = load_market_data(prices=self._saved_prices)
        return self.markets

    def prices(self):
        """Current price of every good, by place. Base prices and events stay in the yaml, so
        a save keeps only what moved and picks up new goods when the yaml changes."""
        if self.markets is None:
            return self._saved_prices
        return {
            place: {good: info["currentPrice"] for good, info in ((market or {}).get("goods") or {}).items()}
            for place, market in self.markets.items()
        }

    def npc_state(self, npc_id, default_mood=0):
        state = self.npcs.get(npc_id)
        if state is None:
            state = {"mood": default_mood, "vars": {}, "visited": {}}
            self.npcs[npc_id] = state
        return state

    def to_dict(self):
        return {
            "globals": self.globals,
            "npcs": self.npcs,
            "rosters": self.rosters,
            "news": self.news,
            "prices": self.prices(),
        }
