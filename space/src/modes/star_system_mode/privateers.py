"""Faction privateers: hunters on the turn clock.

Each action a privateer decides what it will do next, its intent, which a scan reveals.
A shot is only fired on an action whose intent was to fire, so a scanned privateer always
warns you a turn ahead. Each action it then patrols, hunts, searches, engages or retreats:

- patrol: wander near home, pinging now and then.
- hunt: head for its last fix on the player (from a ping, or where it lost sight).
- search: no contact at the fix; wander there pinging, and give up after a while.
- engage: in sight; close to weapon range and hold there, shield up, firing when charged.
- retreat: badly hurt; run home, boosting while fuel lasts.

They never fly into the sun's glare or Assembly patrol zones, break off when the player is
inside a patrol zone, and leave friends of their sponsor alone.
"""
import math
import random

from entities.player import Ship
from util.config import TILE_SIZE, resolve_game_path
from util.sprite_animation import TINT_LEVELS, AnimatedSprite
from world.factions import LAW, waves_by

from .combat import WEAPON_RANGE, band, charged

from .shield_fx import draw_shield
from .vessels import Vessel

CLASSES = {
    "cutter": {"speed": 150, "hull": 40, "shield": 30, "power": 0.8},
    "raider": {"speed": 100, "hull": 70, "shield": 50, "power": 1.0},
    "gunship": {"speed": 75, "hull": 120, "shield": 80, "power": 1.5},
}
COLOURS = {"dominion": (179, 66, 78), "cohort": (91, 174, 112), "caravaneers": (204, 115, 63)}
FUEL = 400
BOOST_RESERVE = 100  # stop boosting below this much fuel
CHASE_BOOST_PX = 600  # boost to close a gap wider than this
ENGAGE_RANGE = 8 * TILE_SIZE  # weapon range they close to and hold
ARRIVED = 3 * TILE_SIZE
RETREAT_AT = 0.4  # share of hull left when they run
HUNT_PING_EVERY = 4
PATROL_PING_EVERY = 12
PATROL_WANDER = 2000  # px around home
SEARCH_WANDER = 6 * TILE_SIZE
SEARCH_TURNS = 12  # turns without contact before giving up
SEARCH_PER_STANDING = 5  # one more turn of searching per this much Assembly standing
FRAME = (48, 48)
FRAMES = 6
_DIRECTIONS = {
    (0, -1): "north", (1, -1): "northeast", (1, 0): "east", (1, 1): "southeast",
    (0, 1): "south", (-1, 1): "southwest", (-1, 0): "west", (-1, -1): "northwest",
}

PATROL, HUNT, SEARCH, ENGAGE, RETREAT = "patrol", "hunt", "search", "engage", "retreat"


def search_turns(reputation):
    """The friendlier you are with the Assembly, the longer raiders keep looking for you."""
    return SEARCH_TURNS + max(0, reputation.get(LAW, 0)) // SEARCH_PER_STANDING


class Privateer(Vessel):
    def __init__(self, kind, sponsor, position, mode, home=None, rng=random):
        stats = CLASSES[kind]
        self.ship = Ship()  # before Vessel.__init__, which sets shield_up through the property
        super().__init__(position)
        self.kind = kind
        self.sponsor = sponsor
        self.mode = mode
        self.home = home or self.position
        self.rng = rng
        self.base_speed = stats["speed"]
        self.ship.max_hull = self.ship.hull = stats["hull"]
        self.ship.max_shield = self.ship.shield = stats["shield"]
        self.ship.max_fuel = self.ship.fuel = FUEL
        self.state = PATROL
        self.waypoint = None
        self.turns = 0
        self.heading = "south"
        self.colour = COLOURS[sponsor]
        self.power = stats["power"]
        self.intent = (PATROL, None)  # (what it means to do next, hit chance if firing)
        self.scanned = False
        self._sprite = None

    # Shield and speed follow the ship and its boost.
    @property
    def shield_up(self):
        return self.ship.shield_up

    @shield_up.setter
    def shield_up(self, up):
        self.ship.shield_up = up

    @property
    def speed(self):
        return self.base_speed * (2 if self.boosting else 1)

    def take_turn(self):
        self.turns += 1
        self.moved = self.boosting = self.fired = False
        mode = self.mode
        me = mode.ship_center()
        if self.ship.hull <= self.ship.max_hull * RETREAT_AT:
            self.state = RETREAT
        elif waves_by(mode.player.reputation, self.sponsor) or mode.selected_system.in_patrol_zone(me):
            self.forget()
        elif mode.seen_by(self):
            self.player_fix = (me, mode.clock.now)
            self.state = ENGAGE
        elif self.state == ENGAGE or (self.state == PATROL and self.player_fix):
            self.state = HUNT
        getattr(self, "_" + self.state)()
        # Engaged with charge to fire, the shield is up; dry, it drops to recharge faster.
        self.ship.shield_up = self.state == ENGAGE and charged(self.ship)
        self.ship.end_turn()
        self.intent = self.plan_next()

    def can_fire(self):
        mode = self.mode
        me = mode.ship_center()
        return (charged(self.ship) and mode.seen_by(self) and math.dist(self.position, me) <= WEAPON_RANGE
                and not mode.sensors.blind(self.position) and not mode.sensors.blind(me))

    def plan_next(self):
        """What this privateer will try next action. Shown above it once scanned."""
        if self.state == RETREAT:
            return ("retreat", None)
        if self.state == ENGAGE:
            if self.can_fire():
                return ("fire", band(math.dist(self.position, self.mode.ship_center()))[0])
            if math.dist(self.position, self.mode.ship_center()) > ENGAGE_RANGE + TILE_SIZE:
                return ("close", None)
            return ("hold", None)
        every = HUNT_PING_EVERY if self.state in (HUNT, SEARCH) else PATROL_PING_EVERY
        if (self.turns + 1) % every == 0:
            return ("ping", None)
        return ("close", None) if self.state == HUNT else (self.state, None)

    def hunting(self):
        return self.state in (HUNT, SEARCH, ENGAGE)

    def forget(self):
        self.player_fix = None
        self.scanned = False  # the encounter is over
        if self.state != RETREAT:
            self.state = PATROL

    def _patrol(self):
        if self.turns % PATROL_PING_EVERY == 0:
            self.mode.vessel_ping(self)
            return
        if self.waypoint is None or math.dist(self.position, self.waypoint) <= ARRIVED:
            self.waypoint = self._open_point(self.home, PATROL_WANDER)
        self.step(self.waypoint)

    def _hunt(self):
        if self.turns % HUNT_PING_EVERY == 0:
            self.mode.vessel_ping(self)
            return
        target = self.player_fix[0]
        if math.dist(self.position, target) <= ARRIVED:
            self.state = SEARCH
            self.waypoint = None
            self.mode.vessel_ping(self)
            return
        self.boost_if(math.dist(self.position, target) > CHASE_BOOST_PX)
        self.step(target)

    def _search(self):
        fix, seen_at = self.player_fix
        if self.mode.clock.now - seen_at > search_turns(self.mode.player.reputation):
            self.forget()
            return
        if math.dist(self.position, fix) > SEARCH_WANDER + ARRIVED:
            self.state = HUNT  # a ping placed the player somewhere new
            return
        if self.turns % HUNT_PING_EVERY == 0:
            self.mode.vessel_ping(self)
            return
        if self.waypoint is None or math.dist(self.position, self.waypoint) <= ARRIVED:
            self.waypoint = self._open_point(fix, SEARCH_WANDER)
        self.step(self.waypoint)

    def _engage(self):
        if self.intent[0] == "fire" and self.can_fire():
            self.fired = True
            self.mode.privateer_fire(self)
            return
        target = self.mode.ship_center()
        distance = math.dist(self.position, target)
        if distance > ENGAGE_RANGE + TILE_SIZE:
            self.boost_if(distance > CHASE_BOOST_PX)
            self.step(target)
        elif distance < ENGAGE_RANGE - 2 * TILE_SIZE:
            self.step(target, away=True)

    def _retreat(self):
        if math.dist(self.position, self.home) > ARRIVED:
            self.boost_if(True)
            self.step(self.home)

    def boost_if(self, wanted):
        self.boosting = wanted and self.ship.fuel > BOOST_RESERVE

    def _allowed(self, point, leaving_zone):
        system = self.mode.selected_system
        if self.mode.sensors.blind(point):
            return False
        return leaving_zone or not system.in_patrol_zone(point)

    def _open_point(self, centre, radius):
        """A random spot near `centre` outside the glare and patrol zones (or centre itself)."""
        for _ in range(12):
            angle = self.rng.uniform(0, 2 * math.pi)
            distance = self.rng.uniform(0, radius)
            point = (centre[0] + distance * math.cos(angle), centre[1] + distance * math.sin(angle))
            if self._allowed(point, False):
                return point
        return centre

    def step(self, target, away=False):
        """One tile toward (or away from) `target`, never into glare or a patrol zone."""
        x, y = self.position
        leaving_zone = self.mode.selected_system.in_patrol_zone(self.position)
        here = math.dist(self.position, target)
        best = None
        for (dx, dy) in _DIRECTIONS:
            point = (x + dx * TILE_SIZE, y + dy * TILE_SIZE)
            if not self._allowed(point, leaving_zone):
                continue
            score = -math.dist(point, target) if away else math.dist(point, target)
            if best is None or score < best[0]:
                best = (score, point, (dx, dy))
        if best is None or (not away and best[0] >= here):
            self.boosting = False  # boxed in, or no tile gets closer: hold position
            return
        _, self.position, direction = best
        self.heading = _DIRECTIONS[direction]
        self.moved = True
        self.ship.burn_fuel(multiplier=2 if self.boosting else 1)

    # Drawing, only once the player can see it.
    def sprite(self):
        if self._sprite is None:
            path = resolve_game_path(f"space/assets/img/ships/privateer_{self.kind}_{self.sponsor}.png")
            self._sprite = AnimatedSprite(path, FRAME, FRAMES, animation_cooldown_ms=90)
        return self._sprite

    def draw(self, screen, centre, now_ms):
        sprite = self.sprite()
        sprite.update()
        damage = 1 - self.ship.hull / self.ship.max_hull
        tint = min(TINT_LEVELS - 1, int(damage * TINT_LEVELS))
        top_left = (centre[0] - FRAME[0] // 2, centre[1] - FRAME[1] // 2)
        frame, position = sprite.blit_position(self.heading, top_left, tint)
        screen.blit(frame, position)
        if self.ship.shield_up:
            draw_shield(screen, centre, self.ship.shield / self.ship.max_shield, now_ms)
