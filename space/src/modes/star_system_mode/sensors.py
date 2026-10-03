"""Hunt and hide: how loud a ship is, who can see whom, and pings that find and give away.

A ship's signature is the range at which others sense it, and sensing works the same both
ways: an observer sees a ship within that ship's signature. Nobody sees into or out of the
sun's glare, which is its heat zone.
"""
import math
import random

from .nav_charts import MAX_HALF_WIDTH_DEG, MIN_HALF_WIDTH_DEG, PIXELS_PER_DEGREE

SIGNATURE_DARK = 300  # held still with the shield down: running dark
SIGNATURE_CRUISE = 700  # any move
SIGNATURE_SHIELD = 500
SIGNATURE_BOOST = 500
SIGNATURE_CARGO = 400  # at a full hold
SIGNATURE_MAX = SIGNATURE_CRUISE + SIGNATURE_SHIELD + SIGNATURE_BOOST + SIGNATURE_CARGO
PING_RANGE = 6000  # an area ping finds, and is heard by, ships this close
RING_SPEED = 2500  # px per second the visible ping ring spreads
WEDGE_TURNS = 4  # bearing wedges fade over this many turns


def signature(moved, shield_up, boosting, cargo_fill=0.0):
    loudness = SIGNATURE_CRUISE if moved else SIGNATURE_DARK
    if shield_up:
        loudness += SIGNATURE_SHIELD
    if boosting:
        loudness += SIGNATURE_BOOST
    return loudness + SIGNATURE_CARGO * max(0.0, min(1.0, cargo_fill))


def bearing(origin, point):
    """Screen-space degrees from `origin` to `point` (0 = east, y down)."""
    return math.degrees(math.atan2(point[1] - origin[1], point[0] - origin[0]))


def spread(distance):
    """Half-width of a bearing wedge: farther contacts give vaguer bearings."""
    return min(max(distance / PIXELS_PER_DEGREE, MIN_HALF_WIDTH_DEG), MAX_HALF_WIDTH_DEG)


class Wedge:
    """A bearing toward something a ping found, fading over WEDGE_TURNS."""

    def __init__(self, origin, angle, half_width, turn, hostile):
        self.origin = origin
        self.angle = angle
        self.half_width = half_width
        self.turn = turn
        self.hostile = hostile

    def strength(self, now_turn):
        return max(0.0, 1 - (now_turn - self.turn) / WEDGE_TURNS)


class Ring:
    """The visible pulse of an area ping, spreading at RING_SPEED."""

    def __init__(self, origin, started_ms, hostile):
        self.origin = origin
        self.started_ms = started_ms
        self.hostile = hostile

    def radius(self, now_ms):
        return RING_SPEED * max(0, now_ms - self.started_ms) / 1000

    def done(self, now_ms):
        return self.radius(now_ms) > PING_RANGE


class Sensors:
    def __init__(self, system, rng=random):
        self.system = system
        self.rng = rng
        self.wedges = []
        self.rings = []

    def blind(self, point):
        """Inside the sun's glare nothing can lock, ping or scan, in or out."""
        return self.system.heat_at(point) > 0

    def sees(self, observer, target, target_signature):
        if self.blind(observer) or self.blind(target):
            return False
        return math.dist(observer, target) <= target_signature

    def in_ping_range(self, origin, point):
        if self.blind(origin) or self.blind(point):
            return False
        return math.dist(origin, point) <= PING_RANGE

    def pulse(self, origin, now_ms, hostile):
        self.rings.append(Ring(origin, now_ms, hostile))

    def mark(self, origin, target, turn, hostile):
        """A wedge from `origin` toward `target`. The true bearing always lies inside it."""
        half = spread(math.dist(origin, target))
        angle = bearing(origin, target) + self.rng.uniform(-half / 2, half / 2)
        self.wedges.append(Wedge(origin, angle, half, turn, hostile))

    def prune(self, now_turn, now_ms):
        self.wedges = [w for w in self.wedges if w.strength(now_turn) > 0]
        self.rings = [r for r in self.rings if not r.done(now_ms)]
