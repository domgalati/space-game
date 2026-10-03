"""Ship weapons: instant hits whose chance and damage fall off with range, fired from the shield.

The shield is the battery. A shot spends SHOT_COST charge whether the shield is raised or not,
is loud for that turn, and stops the shield recharging that turn. Privateers fire by the same
rules, with a damage multiplier per class.
"""
import math

from util.config import TILE_SIZE

# (out to this range, hit chance, damage, name), closest first.
# A shot is worth more than the charge it costs, so emptying a battery decides a fight.
BANDS = (
    (4 * TILE_SIZE, 0.90, 20, "CLOSE"),
    (8 * TILE_SIZE, 0.65, 14, "EFFECTIVE"),
    (12 * TILE_SIZE, 0.35, 8, "LONG"),
)
WEAPON_RANGE = BANDS[-1][0]
SHOT_COST = 12  # shield charge per shot
SCAN_RANGE = 20 * TILE_SIZE
SHOT_MS = 140  # how long a shot's beam stays on screen
MISS_SHORT = 0.82  # a miss's beam stops this share of the way and sparks


def band(distance):
    """(hit chance, damage, name) at `distance`, or None beyond weapon range."""
    for reach, chance, damage, name in BANDS:
        if distance <= reach:
            return chance, damage, name
    return None


def charged(ship):
    return ship.shield >= SHOT_COST


class Shot:
    """A fired shot, for drawing: from shooter to target (or short of it on a miss)."""

    def __init__(self, start, end, hit, colour, until_ms):
        self.start = start
        self.end = end if hit else (start[0] + (end[0] - start[0]) * MISS_SHORT,
                                    start[1] + (end[1] - start[1]) * MISS_SHORT)
        self.hit = hit
        self.colour = colour
        self.until_ms = until_ms


def fire(shooter, target, start, end, rng, power=1.0):
    """Spend a shot's charge and roll it. Returns (hit, damage to shield, damage to hull)."""
    shooter.shield -= SHOT_COST
    shooter.hit_this_turn = True  # firing drains the battery like a hit: no recharge this turn
    chance, damage, _ = band(math.dist(start, end))
    if rng.random() >= chance:
        return False, 0, 0
    to_shield, to_hull = target.take_damage(damage * power)
    return True, to_shield, to_hull
