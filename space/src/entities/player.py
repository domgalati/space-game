## The classes in this file represent what values are stored when the player saves the game.

FUEL_PER_STEP = 0.25  # cruise burn per tile flown in star system mode
DOCK_FUEL = 6  # spent when a dock actually succeeds

class Player:
    def __init__(self):
        self.health = 100
        self.energy = 100
        self.inventory = Inventory(capacity=20)
        self.personal_equipment = []
        self.stats = {'strength': 10, 'intelligence': 10}
        self.currency = 0
        self.reputation = {'assembly': 0, 'caravaneers': 0, 'cohort': 0, 'dominion': 0}
        self.charted_planets = set()
        self.ship = Ship()

class Ship:
    def __init__(self):
        self.health = 100
        self.max_fuel = 1000
        self.fuel = 1000
        self.equipment = []
        self.stats = {'hull': 10, 'cargo_space': 10, 'speed': 10}
        self.cargo = Inventory(capacity=100)

    def burn_fuel(self, steps=1, multiplier=1.0, amount=None):
        cost = amount if amount is not None else FUEL_PER_STEP * steps * multiplier
        self.fuel = max(0.0, self.fuel - cost)

    @property
    def on_reserve(self):
        return self.fuel <= 0

class Inventory:
    def __init__(self, capacity):
        self.capacity = capacity
        self.items = {}

    def add_item(self, item, quantity):
        if self.get_total_quantity() + quantity > self.capacity:
            return False  # Inventory full
        self.items[item] = self.items.get(item, 0) + quantity
        return True

    def remove_item(self, item, quantity):
        if self.items.get(item, 0) < quantity:
            return False  # Not enough items
        self.items[item] -= quantity
        if self.items[item] == 0:
            del self.items[item]
        return True

    def get_total_quantity(self):
        return sum(self.items.values())

    def __str__(self):
        return f"Inventory({self.items}, Capacity: {self.capacity})"