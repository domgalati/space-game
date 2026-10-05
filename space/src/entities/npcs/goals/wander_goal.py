import random

from .base_goal import BaseGoal


class WanderGoal(BaseGoal):
    """One random step per turn (player move advances time)."""

    activity = "just stretching my legs"

    def update(self, ground):
        steps = self.open_steps(ground)
        if steps:
            ground.move(self.npc, random.choice(steps))
