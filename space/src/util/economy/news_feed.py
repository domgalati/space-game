"""What the player has heard: fired market events, and when each market was last scanned or visited.

Time is counted in landings. Stored in the world save under ``news``.
"""

FRESH_TICKS = 3  # landings before a market check, and the stories it carried, go stale
MAX_STORIES = 12


class NewsFeed:
    def __init__(self, world_state):
        self.state = world_state.news
        self.state.setdefault("tick", 0)
        self.state.setdefault("seq", 0)  # orders records and checks within the same landing
        self.state.setdefault("stories", [])
        self.state.setdefault("intel", {})

    @property
    def tick(self):
        return self.state["tick"]

    @property
    def stories(self):
        return self.state["stories"]

    @property
    def intel(self):
        return self.state["intel"]

    def advance(self):
        """One landing's worth of time passes."""
        self.state["tick"] += 1
        self._prune()

    def _next_seq(self):
        self.state["seq"] += 1
        return self.state["seq"]

    def _prune(self):
        fresh = [story for story in self.stories if self.tick - story["tick"] <= FRESH_TICKS]
        self.state["stories"] = fresh[-MAX_STORIES:]

    def record(self, place, event, moves):
        """A fired event; ``moves`` is a list of {good, price, change}."""
        if not moves:
            return
        self.stories.append({
            "tick": self.tick, "seq": self._next_seq(), "place": place, "event": event, "moves": list(moves),
        })
        self._prune()

    def observe(self, place, goods):
        """The player checked this market: remember when, and what everything cost."""
        if not goods:
            return
        self.intel[place] = {
            "tick": self.tick,
            "seq": self._next_seq(),
            "goods": {
                good: {"price": int(round(info["currentPrice"])), "base": info["basePrice"]}
                for good, info in goods.items()
            },
        }

    def age(self, place):
        """Landings since this market was last checked, or None if never."""
        seen = self.intel.get(place)
        return None if seen is None else self.tick - seen["tick"]

    def is_fresh(self, place):
        age = self.age(place)
        return age is not None and age <= FRESH_TICKS

    def known_stories(self):
        """Stories the player has picked up, newest first: checked since it fired, and still fresh."""
        return [
            story for story in reversed(self.stories)
            if self.is_fresh(story["place"]) and self.intel[story["place"]]["seq"] > story["seq"]
        ]

    def market_status(self, places):
        """(place, age or None) for every market, plus any checked market not in ``places``."""
        names = list(dict.fromkeys([*places, *self.intel]))
        return [(place, self.age(place)) for place in names]
