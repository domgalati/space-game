from entities.actor import Actor
from entities.npcs.goals.wander_goal import WanderGoal


class NPC(Actor):
    """Someone the player meets ashore: an Actor with a job, a look, a voice and a goal."""

    def __init__(self):
        super().__init__()
        self.npc_id = None
        self.sprite = None
        self.species = "human"
        self.portrait_recipe = None
        self.dialogue_file = None
        self.start_node = "Start"
        self.base_mood = None
        self.firstname = None
        self.lastname = None
        self.hobbies = []
        self.job_title = None
        self.goal = WanderGoal(self)

    def update(self, ground):
        """Take a turn on `ground` (a GroundMap)."""
        if self.goal:
            self.goal.update(ground)
        