"""The player, their ship and where they are: everything about them a save keeps (world.save).

Each class turns itself into plain data (to_dict) and back (from_dict). Keys a save lacks
keep a new player's defaults, so adding a field doesn't break older saves.
"""
from entities.actor import Actor
from entities.inventory import Inventory

FUEL_PER_STEP = 0.25  # cruise burn per tile flown in star system mode
DOCK_FUEL = 6  # spent when a dock actually succeeds
SHIELD_RECHARGE = 2  # per clean turn while raised; empty to full in 50 moves
SHIELD_RECHARGE_DOWN = 5  # per clean turn while lowered; empty to full in 20 moves

class Player(Actor):
    def __init__(self):
        super().__init__()
        self.charted_planets = set()  # body ids (world.atlas) the nav computer has a fix on
        self.trade_ledger = {}  # credits traded per faction, for standing earned by trade
        self.kill_log = []  # privateers destroyed, for bounties
        self.ship = Ship()
        self.location = Location()

    def to_dict(self):
        return {
            **super().to_dict(),
            "trade_ledger": dict(self.trade_ledger),
            "kill_log": [dict(kill) for kill in self.kill_log],
            "charted_planets": sorted(self.charted_planets),
            "ship": self.ship.to_dict(),
            "location": self.location.to_dict(),
        }

    @classmethod
    def from_dict(cls, data):
        player = cls().load(data)
        player.trade_ledger.update(data.get("trade_ledger") or {})
        player.kill_log = [dict(kill) for kill in data.get("kill_log") or ()]
        player.charted_planets = set(data.get("charted_planets") or ())
        if "ship" in data:
            player.ship = Ship.from_dict(data["ship"])
        if "location" in data:
            player.location = Location.from_dict(data["location"])
        return player

class Location:
    """Where the player is: a star system, the body they are docked at (None in flight),
    and the ship's tile in that system, kept while docked so departure resumes there."""

    def __init__(self, system=None, body=None, tile=None):
        self.system = system  # system id, e.g. "sol"
        self.body = body  # body id, e.g. "sol/terramonta", or None
        self.tile = tile  # (x, y) in the system's tile grid, or None before the first flight

    def to_dict(self):
        return {"system": self.system, "body": self.body, "tile": list(self.tile) if self.tile else None}

    @classmethod
    def from_dict(cls, data):
        tile = data.get("tile")
        return cls(data.get("system"), data.get("body"), tuple(tile) if tile else None)

class Ship:
    def __init__(self):
        self.max_hull = 100
        self.hull = 100
        self.max_shield = 100
        self.shield = 100
        self.shield_up = False
        self.hit_this_turn = False
        self.max_fuel = 1000
        self.fuel = 1000
        self.equipment = []
        self.stats = {'hull': 10, 'cargo_space': 10, 'speed': 10}
        self.cargo = Inventory(capacity=100)

    SAVED = ("max_hull", "hull", "max_shield", "shield", "shield_up", "max_fuel", "fuel", "equipment", "stats")

    def to_dict(self):
        data = {key: getattr(self, key) for key in self.SAVED}
        data["cargo"] = self.cargo.to_dict()
        return data

    @classmethod
    def from_dict(cls, data):
        ship = cls()
        for key in cls.SAVED:
            if key in data:
                setattr(ship, key, data[key])
        if "cargo" in data:
            ship.cargo = Inventory.from_dict(data["cargo"])
        return ship

    def burn_fuel(self, steps=1, multiplier=1.0, amount=None):
        cost = amount if amount is not None else FUEL_PER_STEP * steps * multiplier
        self.fuel = max(0.0, self.fuel - cost)

    @property
    def on_reserve(self):
        return self.fuel <= 0

    def take_damage(self, amount):
        """A raised shield soaks damage until empty; the rest hits the hull. Returns (shield, hull) taken."""
        if amount <= 0:
            return 0, 0
        to_shield = min(amount, self.shield) if self.shield_up else 0
        self.shield -= to_shield
        to_hull = min(amount - to_shield, self.hull)
        self.hull -= to_hull
        self.hit_this_turn = True
        return to_shield, to_hull

    def end_turn(self):
        """A move that took no damage recharges the shield, faster while it is lowered."""
        if not self.hit_this_turn:
            rate = SHIELD_RECHARGE if self.shield_up else SHIELD_RECHARGE_DOWN
            self.shield = min(self.max_shield, self.shield + rate)
        self.hit_this_turn = False
