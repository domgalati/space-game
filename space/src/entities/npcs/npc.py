from entities.npcs.goals.wander_goal import WanderGoal

class NPC:
    def __init__(self):
        self.firstname = None
        self.lastname = None
        self.hobbies = []
        self.health = 100
        self.energy = 100
        self.inventory = []
        self.personal_equipment = []
        self.currency = 0
        self.reputation = {'assembly': 0, 'caravaneers': 0, 'cohort': 0, 'dominion': 0}
        self.guild = None
        self.level = 1
        self.isBackgroundCharacter = bool
        self.isHostile = bool
        self.position = (0, 0)
        self.goal = WanderGoal(self)
        # Additional attributes as needed

    def update(self):
        if self.goal:
            self.goal.update()        