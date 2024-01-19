import random
from .base_goal import BaseGoal

class WanderGoal(BaseGoal):
    def __init__(self, npc):
        super().__init__(npc)

    def update(self):
        walkable_tiles = self.npc.npc_manager.get_walkable_tiles()
        potential_positions = self.get_adjacent_walkable_positions(walkable_tiles)
        if potential_positions:
            self.npc.position = random.choice(potential_positions)

    def get_adjacent_walkable_positions(self, walkable_tiles):
        x, y = self.npc.position
        adjacent_positions = [
            (x, y - 1),  # Up
            (x, y + 1),  # Down
            (x - 1, y),  # Left
            (x + 1, y)   # Right
        ]
        return [pos for pos in adjacent_positions if pos in walkable_tiles]
