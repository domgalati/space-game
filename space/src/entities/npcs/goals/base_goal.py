class BaseGoal:
    activity = "getting on with my day"  # spoken as "Right now I'm <activity>."

    def __init__(self, npc):
        self.npc = npc

    def update(self, ground):
        """One turn on `ground` (a GroundMap): step with ground.move, or stay put."""

    def open_steps(self, ground):
        """Neighbouring tiles this NPC could step to: walkable, and nobody standing there."""
        return [tile for tile in ground.neighbours(self.npc.position) if ground.free(tile)]
