"""Qud-style time: speed sets how often something acts, and the player's actions spend time.

Speed 100 acts once per turn, 200 twice, 50 every other turn. A player action costs
turns (a cruise move 1, a boosted move 0.5); advancing the clock by that much lets every
other actor take the turns that came due meanwhile, in time order.
"""

SPEED = 100  # baseline: one action per turn
_EPSILON = 1e-9


def turns_for(speed):
    """How long one action takes at `speed`."""
    return SPEED / speed


class Ticker:
    """An actor that only calls `act` on its turns, for upkeep like hazards and recharging."""

    def __init__(self, act, speed=SPEED):
        self.act = act
        self.speed = speed

    def take_turn(self):
        self.act()


class TurnClock:
    def __init__(self):
        self.now = 0.0
        self.actors = []

    @property
    def turn(self):
        return int(self.now + _EPSILON)

    def add(self, actor):
        """`actor` needs `speed` and `take_turn()`; its first turn comes one action from now."""
        actor.next_turn = self.now + turns_for(actor.speed)
        self.actors.append(actor)

    def remove(self, actor):
        if actor in self.actors:
            self.actors.remove(actor)

    def advance(self, turns):
        """Let `turns` of time pass. Actors can be added or removed while it runs."""
        end = self.now + turns
        while self.actors:
            actor = min(self.actors, key=lambda a: a.next_turn)
            if actor.next_turn > end + _EPSILON:
                break
            self.now = actor.next_turn
            actor.take_turn()
            actor.next_turn += turns_for(actor.speed)
        self.now = end
