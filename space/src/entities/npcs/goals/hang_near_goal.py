import random

from .base_goal import BaseGoal


class HangNearGoal(BaseGoal):
    """One biased step toward workplace tiles per turn (player move advances time)."""

    def __init__(self, npc, targets):
        super().__init__(npc)
        self.targets = list(targets) if targets else []

    def update(self):
        walkable_tiles = self.npc.npc_manager.get_walkable_tiles()
        adjacent = self.get_adjacent_walkable_positions(walkable_tiles)
        if not adjacent:
            return

        if not self.targets:
            self.npc.position = random.choice(adjacent)
            return

        current_dist = self._min_distance(self.npc.position)
        improving = [pos for pos in adjacent if self._min_distance(pos) < current_dist]
        if improving:
            self.npc.position = random.choice(improving)
            return

        equal_or_better = [
            pos for pos in adjacent if self._min_distance(pos) <= current_dist
        ]
        self.npc.position = random.choice(equal_or_better or adjacent)

    def _min_distance(self, pos):
        px, py = pos
        return min(abs(px - tx) + abs(py - ty) for tx, ty in self.targets)

    def get_adjacent_walkable_positions(self, walkable_tiles):
        x, y = self.npc.position
        adjacent_positions = [
            (x, y - 1),
            (x, y + 1),
            (x - 1, y),
            (x + 1, y),
        ]
        return [pos for pos in adjacent_positions if pos in walkable_tiles]
