"""Anyone with a body, belongings and allegiances: the player, NPCs, and later ground enemies.

What every person shares lives here, so a fight, a trade or a conversation can treat the
player and an NPC alike. Subclasses add what's theirs alone (the player's ship, an NPC's job).
"""
from entities.inventory import Inventory
from world.factions import FACTIONS

INVENTORY_CAPACITY = 20


class Actor:
    def __init__(self, faction=None, max_health=100, max_energy=100):
        self.faction = faction  # faction id (world.factions), or None for independents
        self.max_health = self.health = max_health
        self.max_energy = self.energy = max_energy
        self.stats = {"strength": 10, "intelligence": 10}
        self.inventory = Inventory(capacity=INVENTORY_CAPACITY)
        self.equipment = {}  # slot -> item id; see world.items
        self.currency = 0
        self.reputation = dict.fromkeys(FACTIONS, 0)  # this actor's standing with each faction
        self.position = None  # (x, y) tile while standing on a GroundMap, else None

    @property
    def alive(self):
        return self.health > 0

    def take_damage(self, amount):
        """Lose up to `amount` health. Returns how much was actually lost."""
        taken = min(max(0, amount), self.health)
        self.health -= taken
        return taken

    def heal(self, amount):
        """Regain up to `amount` health, to max_health. Returns how much was actually regained."""
        healed = min(max(0, amount), self.max_health - self.health)
        self.health += healed
        return healed

    # Saving: subclasses extend both, so a save keeps everything an actor has.
    SAVED = ("faction", "max_health", "health", "max_energy", "energy", "currency")

    def to_dict(self):
        data = {key: getattr(self, key) for key in self.SAVED}
        data.update(
            stats=dict(self.stats),
            reputation=dict(self.reputation),
            equipment=dict(self.equipment),
            inventory=self.inventory.to_dict(),
        )
        return data

    def load(self, data):
        """Take saved values from `data`; keys it lacks keep this actor's defaults."""
        for key in self.SAVED:
            if key in data:
                setattr(self, key, data[key])
        for key in ("stats", "reputation", "equipment"):
            getattr(self, key).update(data.get(key) or {})
        if "inventory" in data:
            self.inventory = Inventory.from_dict(data["inventory"])
        return self
