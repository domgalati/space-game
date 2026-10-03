"""Hunt and hide: how loud a ship is, who can see whom, and pings that find and give away.

A ship's signature is the range at which others sense it, and sensing works the same both
ways: an observer sees a ship within that ship's signature. Nobody sees into or out of the
sun's glare, which is its heat zone.
"""
import math
import random

from .nav_charts import MAX_HALF_WIDTH_DEG, MIN_HALF_WIDTH_DEG, PIXELS_PER_DEGREE, _heading

SIGNATURE_DARK = 300  # held still with the shield down: running dark
SIGNATURE_CRUISE = 700  # any move
SIGNATURE_SHIELD = 500
SIGNATURE_BOOST = 500
SIGNATURE_CARGO = 400  # at a full hold
SIGNATURE_FIRING = 900  # the turn a ship fires
SIGNATURE_MAX = SIGNATURE_CRUISE + SIGNATURE_SHIELD + SIGNATURE_BOOST + SIGNATURE_CARGO + SIGNATURE_FIRING
PING_RANGE = 6000  # an area ping is heard this far, and finds a loud ship this far
PING_DARK_RANGE = 3000  # a ship running dark is only found this close
LOUD_AT = 1200  # at this signature or more, a ping finds you at its full range
PING_SPEED = 1000  # px per turn an enemy ping's wavefront travels; you're caught or missed when it arrives
RING_SPEED = 2500  # px per second your own ping's ring spreads on screen
WEDGE_TURNS = 4  # bearing wedges fade over this many turns


def signature(moved, shield_up, boosting, cargo_fill=0.0, fired=False):
    loudness = SIGNATURE_CRUISE if moved else SIGNATURE_DARK
    if shield_up:
        loudness += SIGNATURE_SHIELD
    if boosting:
        loudness += SIGNATURE_BOOST
    if fired:
        loudness += SIGNATURE_FIRING
    return loudness + SIGNATURE_CARGO * max(0.0, min(1.0, cargo_fill))


def catch_range(loudness):
    """How close a ping must be to find a ship this loud: 3000 running dark, 6000 at LOUD_AT."""
    share = (loudness - SIGNATURE_DARK) / (LOUD_AT - SIGNATURE_DARK)
    return PING_DARK_RANGE + (PING_RANGE - PING_DARK_RANGE) * max(0.0, min(1.0, share))


def loudest_unfound(distance):
    """The loudest signature a ping from `distance` away misses, or None if nothing would."""
    if distance <= PING_DARK_RANGE:
        return None
    share = (distance - PING_DARK_RANGE) / (PING_RANGE - PING_DARK_RANGE)
    return SIGNATURE_DARK + (LOUD_AT - SIGNATURE_DARK) * share


def compass(origin, point):
    return _heading(bearing(origin, point))[1]


def range_label(distance):
    """Ping ranges are rough: to the nearest 100 m (a pixel is a metre)."""
    return f"{int(round(distance, -2))} m"


def bearing(origin, point):
    """Screen-space degrees from `origin` to `point` (0 = east, y down)."""
    return math.degrees(math.atan2(point[1] - origin[1], point[0] - origin[0]))


def spread(distance):
    """Half-width of a bearing wedge: farther contacts give vaguer bearings."""
    return min(max(distance / PIXELS_PER_DEGREE, MIN_HALF_WIDTH_DEG), MAX_HALF_WIDTH_DEG)


class Wedge:
    """A bearing and rough range toward something a ping found, fading over WEDGE_TURNS."""

    def __init__(self, origin, angle, half_width, turn, hostile, distance):
        self.origin = origin
        self.angle = angle
        self.half_width = half_width
        self.turn = turn
        self.hostile = hostile
        self.distance = distance

    def strength(self, now_turn):
        return max(0.0, 1 - (now_turn - self.turn) / WEDGE_TURNS)


class Ring:
    """The pulse of an area ping. Yours spreads in real time; an enemy's travels PING_SPEED per
    turn, so you see it coming and it only catches or misses you when it arrives."""

    def __init__(self, origin, hostile, started_ms=0, start_turn=None, pinger=None):
        self.origin = origin
        self.hostile = hostile
        self.started_ms = started_ms
        self.start_turn = start_turn
        self.pinger = pinger
        self.resolved = False

    def radius(self, now_ms, now_turn):
        if self.start_turn is not None:
            return PING_SPEED * max(0.0, now_turn - self.start_turn)
        return RING_SPEED * max(0, now_ms - self.started_ms) / 1000

    def done(self, now_ms, now_turn):
        return self.radius(now_ms, now_turn) > PING_RANGE


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

    def catches(self, origin, point, loudness):
        """Whether a ping from `origin` finds a ship at `point` making `loudness`."""
        return self.in_ping_range(origin, point) and math.dist(origin, point) <= catch_range(loudness)

    def pulse(self, origin, now_ms):
        self.rings.append(Ring(origin, hostile=False, started_ms=now_ms))

    def enemy_pulse(self, origin, turn, pinger):
        ring = Ring(origin, hostile=True, start_turn=turn, pinger=pinger)
        self.rings.append(ring)
        return ring

    def mark(self, origin, target, turn, hostile):
        """A wedge from `origin` toward `target`. The true bearing always lies inside it."""
        distance = math.dist(origin, target)
        half = spread(distance)
        angle = bearing(origin, target) + self.rng.uniform(-half / 2, half / 2)
        self.wedges.append(Wedge(origin, angle, half, turn, hostile, distance))

    def prune(self, now_turn, now_ms):
        self.wedges = [w for w in self.wedges if w.strength(now_turn) > 0]
        self.rings = [r for r in self.rings if not r.done(now_ms, now_turn)]
