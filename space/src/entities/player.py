## The classes in this file represent what values are stored when the player saves the game.

class Player:
    def __init__(self):
        self.health = 100
        self.energy = 100
        self.inventory = []
        self.personal_equipment = []
        self.stats = {'strength': 10, 'intelligence': 10}
        self.currency = 0
        self.reputation = {'assembly': 0, 'caravaneers': 0, 'cohort': 0, 'dominion': 0}
        # Additional attributes as needed

class Ship:
    def __init__(self):
        self.health = 100
        self.fuel = 100
        self.equipment = []
        self.stats = {'strength': 10, 'intelligence': 10}
        self.cargo = []
        self.speed = 10  # km/h
        self.fuel_consumption = 10  # kg/km
        self.fuel_capacity = 100  # kg
