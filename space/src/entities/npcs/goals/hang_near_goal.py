import random

from .base_goal import BaseGoal


class HangNearGoal(BaseGoal):
    """One biased step toward workplace tiles per turn (player move advances time)."""

    activity = "sticking close to my post"

    def __init__(self, npc, targets, activity=None):
        super().__init__(npc)
        self.targets = list(targets) if targets else []
        if activity:
            self.activity = activity

    def update(self, ground):
        adjacent = self.open_steps(ground)
        if not adjacent:
            return

        if not self.targets:
            ground.move(self.npc, random.choice(adjacent))
            return

        current_dist = self._min_distance(self.npc.position)
        improving = [pos for pos in adjacent if self._min_distance(pos) < current_dist]
        if improving:
            ground.move(self.npc, random.choice(improving))
            return

        equal_or_better = [
            pos for pos in adjacent if self._min_distance(pos) <= current_dist
        ]
        ground.move(self.npc, random.choice(equal_or_better or adjacent))

    def _min_distance(self, pos):
        px, py = pos
        return min(abs(px - tx) + abs(py - ty) for tx, ty in self.targets)
