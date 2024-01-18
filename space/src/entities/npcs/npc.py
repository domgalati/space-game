## The classes in this file represent what values are stored when the player saves the game.

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
        # Additional attributes as needed