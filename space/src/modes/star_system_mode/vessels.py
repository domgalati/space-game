"""Other ships in flight. Each is a turn-clock actor with a position and a signature."""
import random

from util.config import TILE_SIZE
from util.turns import SPEED

from .sensors import signature

DRONE_PING_EVERY = 4  # turns between a test drone's area pings


class Vessel:
    speed = SPEED

    def __init__(self, position):
        self.position = (float(position[0]), float(position[1]))
        self.shield_up = False
        self.boosting = False
        self.moved = False
        self.cargo_fill = 0.0
        self.player_fix = None  # (position, turn) where a ping last placed the player

    def signature(self):
        return signature(self.moved, self.shield_up, self.boosting, self.cargo_fill)

    def hunting(self):
        """Whether this ship is after the player."""
        return False

    def take_turn(self):
        self.moved = False


class Drone(Vessel):
    """Sensor test target: wanders a tile at a time and area-pings every few turns."""

    def __init__(self, position, mode, rng=random):
        super().__init__(position)
        self.mode = mode
        self.rng = rng
        self.turns = 0

    def take_turn(self):
        self.turns += 1
        if self.turns % DRONE_PING_EVERY == 0:
            self.moved = False
            self.mode.vessel_ping(self)
            return
        dx, dy = self.rng.choice((-1, 0, 1)), self.rng.choice((-1, 0, 1))
        self.position = (self.position[0] + dx * TILE_SIZE, self.position[1] + dy * TILE_SIZE)
        self.moved = bool(dx or dy)
