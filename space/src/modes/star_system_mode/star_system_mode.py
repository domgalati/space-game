# This file handles the main loop when the player is traversing a star system

import math
import random

import pygame
from util.config import SCREEN_WIDTH, SCREEN_HEIGHT, TILE_SIZE, resolve_game_path
from .input_handler import InputHandler, determine_direction, update_parallax
from .nightsky import initialize_stars, draw_stars, PARALLAX_FACTOR, PARALLAX_DAMPING_FACTOR, VELOCITY_THRESHOLD
from util.sprite_animation import TINT_LEVELS, AnimatedSprite
from util.turns import Ticker, TurnClock, turns_for
from .nav_charts import NavCharts
from .scan_terminal import ScanTerminal
from .star_systems import StarSystem
from .shield_fx import draw_shield
from .sensor_fx import OWN, draw_contacts, draw_sensor_overlay
from .sensors import PING_RANGE, PING_SPEED, Sensors, compass, loudest_unfound, range_label, signature
from world.factions import faction_name, record_kill, waves_by
from world.items import item_name
from .combat import SCAN_RANGE, SHOT_MS, Shot, band, charged, fire
from .combat_fx import draw_bracket, draw_intent, draw_shots
from .ui.action_strip import ActionStrip, corridor_rank
from .ui.alerts import DANGER_LEVEL as DANGER, INFO, NOTE, WARNING, Banner, EventLog, PingStrip, PingWarning, draw_log
from .ui.effects import Shake, Vignette
from .ui.enemy_panel import EnemyPanel
from .ui.ship_panel import ShipPanel
from .ui.theme import DANGER as DANGER_COLOUR, HEAT as HEAT_COLOUR, WARN as WARN_COLOUR
from .wrecks import Wreck, roll_salvage
from .vessels import Drone
from .privateers import CLASSES as PRIVATEER_CLASSES, Privateer
from util.economy.news_feed import NewsFeed
from world.world_state import WorldState
from entities.player import DOCK_FUEL
from modes.transitions import Land

CANDIDATE_ARC_COLOR = (255, 191, 0)
NAV_MARKER_COLOR = (120, 220, 140)
NAV_MARKER_MARGIN = 28
RESERVE_SLOWDOWN = 5  # real-time move cooldown multiplier once the tank is empty
BOOST_SCALE = 0.5  # real-time move cooldown while boosting
# Move speeds in turn time (util.turns): a move takes SPEED / speed turns.
CRUISE_SPEED = 100
BOOST_SPEED = 200  # hold shift: half a turn per tile, twice the burn
RESERVE_SPEED = 50  # empty tank: two turns per tile
WAIT_KEY = pygame.K_SPACE
WAIT_TURNS = 1
PING_KEY = pygame.K_p
PING_TURNS = 1
FIRE_KEY = pygame.K_f
SCAN_KEY = pygame.K_r
TARGET_KEY = pygame.K_TAB
FIRE_TURNS = 1
SCAN_TURNS = 1
TARGET_COLOR = (255, 255, 255)
RING_EASE = 12  # how quickly enemy rings glide to their new radius after a turn, per second
TEST_DRONE_RANGE = (900, 3500)  # px from the ship where debug drones appear
TEST_PRIVATEER_RANGE = (3500, 6000)  # px from the ship where debug privateers start patrolling
TOW_FEE = 0.1  # share of credits the tug charges when the hull fails
BOOST_BURN = 2.0
RING_BAND = 160  # px from a charted orbit that counts as riding the ring
RING_BURN = 0.5
ATMO_BURN = 2.0
BEACON_COLOR = (0, 196, 32)
BEACON_DIM = (207, 192, 65)
SHIELD_KEY = pygame.K_s
SHIELD_FADE_MS = 160  # shell fades in or out over this long
SHIELD_FLASH_MS = 140  # shell flashes this long after absorbing a hit
CRITICAL_HULL = 0.2  # below this the damage tint flickers

class StarSystemMode:
    def __init__(self, player, starsystem, world_state=None):
        self.player = player
        self.world_state = world_state or WorldState()
        self.news_feed = NewsFeed(self.world_state)
        self.selected_system = StarSystem(resolve_game_path(f"space/star_systems/{starsystem}.json"))
        self.input_handler = InputHandler()
        self.cruise_cooldown = self.input_handler.movement_cooldown
        self.grid_size = (self.selected_system.MAP_WIDTH // TILE_SIZE, self.selected_system.MAP_HEIGHT // TILE_SIZE)
        self.white_stars, self.purple_stars, self.blue_stars = initialize_stars(SCREEN_WIDTH, SCREEN_HEIGHT)
        self.map_center_x = self.selected_system.MAP_WIDTH // 2
        self.map_center_y = self.selected_system.MAP_HEIGHT // 2
        self.cargo_sheet = 'space/assets/img/barge6frame.png'
        self.frame_dimensions = (48, 48)
        self.num_frames = 6
        self.animated_cargoship = AnimatedSprite(
            resolve_game_path(self.cargo_sheet), self.frame_dimensions, self.num_frames,
            animation_cooldown_ms=90,
        )
        self.current_direction = "southeast"
        location = player.location
        if location.system != self.selected_system.id or location.tile is None:
            spawn_x, spawn_y = self.selected_system.spawn_point()
            location.system = self.selected_system.id
            location.tile = (int(spawn_x) // TILE_SIZE, int(spawn_y) // TILE_SIZE)
        self.previous_x, self.previous_y = self.x_position, self.y_position
        self.parallax_offset_x, self.parallax_offset_y = 0, 0
        self.parallax_velocity_x, self.parallax_velocity_y = 0, 0
        self.camera = pygame.Rect(0, 0, SCREEN_WIDTH, SCREEN_HEIGHT)
        self.scan_terminal = None
        self.elapsed = 0.0  # seconds this mode has been updated; paces held keys
        self.pending = None  # transition for update() to hand back, e.g. Land after docking
        self.nav = NavCharts((self.map_center_x, self.map_center_y), player.charted_planets)
        self.nav_font = pygame.font.Font(resolve_game_path("space/assets/fonts/OfficeCodePro-Light.ttf"), 14)
        self.boosting = False
        self.clock = TurnClock()
        self.clock.add(Ticker(self.upkeep_turn))
        self.sensors = Sensors(self.selected_system)
        self.vessels = []
        self.last_action = "wait"  # "move", "wait" or "ping"; moving is what makes you loud
        self.ring_turn = 0.0  # the clock as enemy rings are drawn, easing toward the real one
        self.target = None  # the vessel F fires at and R scans
        self.shots = []
        self.wrecks = []
        self.rng = random.Random()
        self.shield_changed_at = -SHIELD_FADE_MS
        self.shield_flash_until = 0
        self.ship_panel = ShipPanel()
        self.enemy_panel = EnemyPanel()
        self.action_strip = ActionStrip()
        self.banner = Banner()
        self.ping_strip = PingStrip()
        self.events = EventLog()
        self.vignette = Vignette()
        self.shake = Shake()

    # The ship's tile lives on the player's location, so it survives leaving this mode.
    @property
    def x_position(self):
        return self.player.location.tile[0]

    @x_position.setter
    def x_position(self, value):
        self.player.location.tile = (value, self.player.location.tile[1])

    @property
    def y_position(self):
        return self.player.location.tile[1]

    @y_position.setter
    def y_position(self, value):
        self.player.location.tile = (self.player.location.tile[0], value)

    def ship_rect(self):
        return pygame.Rect(self.x_position * TILE_SIZE, self.y_position * TILE_SIZE, TILE_SIZE, TILE_SIZE)

    def ship_center(self):
        rect = self.ship_rect()
        return (rect.centerx, rect.centery)

    def handle_input(self):
        # Handle input specific to this mode
        ship = self.player.ship
        keys = pygame.key.get_pressed()
        self.boosting = (not ship.on_reserve) and (keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT])
        if ship.on_reserve:
            slowdown = RESERVE_SLOWDOWN
        elif self.boosting:
            slowdown = BOOST_SCALE
        else:
            slowdown = 1
        self.input_handler.movement_cooldown = self.cruise_cooldown * slowdown
        before = (self.x_position, self.y_position)
        self.x_position, self.y_position = self.input_handler.handle_movement(self.x_position, self.y_position, self.grid_size, self.elapsed)
        if (self.x_position, self.y_position) != before:
            ship.burn_fuel(multiplier=self.burn_multiplier())
            self.last_action = "move"
            self.spend_turns(self.move_turns())
        elif self.input_handler.handle_wait(WAIT_KEY, self.cruise_cooldown, self.elapsed):
            self.last_action = "wait"
            self.spend_turns(WAIT_TURNS)
        new_direction = determine_direction(self.x_position, self.y_position, self.previous_x, self.previous_y)
        if new_direction:
            self.current_direction = new_direction

    def move_turns(self):
        if self.player.ship.on_reserve:
            return turns_for(RESERVE_SPEED)
        return turns_for(BOOST_SPEED if self.boosting else CRUISE_SPEED)

    def spend_turns(self, turns):
        """The player acted; let the world catch up, then tow the ship home if the hull failed."""
        self.clock.advance(turns)
        self.resolve_pings()
        if self.player.ship.hull <= 0:
            self.tow()

    def upkeep_turn(self):
        """Once per turn: the sun's heat lands, then the shield recharges if nothing hit."""
        ship = self.player.ship
        to_shield, to_hull = ship.take_damage(self.selected_system.heat_at(self.ship_center()))
        if to_shield:
            self.shield_flash_until = pygame.time.get_ticks() + SHIELD_FLASH_MS
        if to_hull:  # one banner that refreshes each turn in the heat, and no shake
            self.notify(f"SOLAR HEAT - HULL -{math.ceil(to_hull)}", DANGER, key="heat", shake=False)
        ship.end_turn()

    def tow(self):
        """Hull failure: a tug hauls the ship back under the station bay, repaired, for a fee."""
        ship = self.player.ship
        fee = int(self.player.currency * TOW_FEE)
        self.player.currency -= fee
        ship.hull = ship.max_hull
        ship.shield = ship.max_shield
        x, y = self.selected_system.spawn_point()
        self.x_position, self.y_position = int(x) // TILE_SIZE, int(y) // TILE_SIZE
        self.previous_x, self.previous_y = self.x_position, self.y_position
        self.target = None
        home = self.selected_system.objects[0].name if self.selected_system.objects else "the station"
        self.notify(f"HULL FAILURE - TOWED TO {home.upper()} - FEE ${fee}", DANGER)
        self.world_state.events.emit("towed", fee=fee, system=self.selected_system.id)

    def notify(self, text, severity=INFO, key=None, shake=None):
        """Log an event, and raise an alert for anything above a NOTE. Warnings glow the screen
        edges amber; danger glows them red and shakes the screen unless `shake` says otherwise."""
        now = pygame.time.get_ticks()
        self.events.add(text, severity, now, key)
        if severity > NOTE:
            self.banner.alerts.post(text, severity, now, key)
        if severity == WARNING:
            self.vignette.glow(WARN_COLOUR, now)
        elif severity == DANGER:
            self.vignette.glow(DANGER_COLOUR, now)
        if (severity == DANGER) if shake is None else shake:
            self.shake.start(now)

    def add_vessel(self, vessel):
        self.vessels.append(vessel)
        self.clock.add(vessel)

    def spawn_test_drones(self, count, rng=None):
        """Sensor test targets that wander near the ship and ping. A debug aid until privateers exist."""
        rng = rng or random.Random(7)
        x, y = self.ship_center()
        for _ in range(count):
            angle = rng.uniform(0, 2 * math.pi)
            distance = rng.uniform(*TEST_DRONE_RANGE)
            self.add_vessel(Drone((x + distance * math.cos(angle), y + distance * math.sin(angle)), self, rng))

    def spawn_test_privateers(self, count, rng=None):
        """Privateers of every class and raider faction patrolling near the ship. A debug aid
        until raids and patrols spawn them for real. None in a system where nobody raids."""
        sponsors = self.selected_system.politics.raiders
        if not sponsors:
            return
        rng = rng or random.Random(11)
        kinds = list(PRIVATEER_CLASSES)
        x, y = self.ship_center()
        for i in range(count):
            for _ in range(20):
                angle = rng.uniform(0, 2 * math.pi)
                distance = rng.uniform(*TEST_PRIVATEER_RANGE)
                point = (x + distance * math.cos(angle), y + distance * math.sin(angle))
                if not self.sensors.blind(point) and not self.selected_system.in_patrol_zone(point):
                    break
            sponsor = sponsors[i % len(sponsors)]
            self.add_vessel(Privateer(kinds[i % len(kinds)], sponsor, point, self, rng=rng))

    def player_signature(self):
        ship = self.player.ship
        moved = self.last_action == "move"
        cargo = ship.cargo
        return signature(moved, ship.shield_up, moved and self.boosting, cargo.get_total_quantity() / cargo.capacity,
                         fired=self.last_action == "fire")

    # Fighting: targets, firing, scanning, kills and salvage.
    def combat_targets(self):
        """Armed ships you can sense, nearest first."""
        me = self.ship_center()
        armed = [v for v in self.vessels if v.armed and self.sees(v)]
        return sorted(armed, key=lambda v: math.dist(me, v.position))

    def current_target(self):
        """The target while you can still sense it, else the nearest armed contact (or None)."""
        if self.target is None or self.target not in self.vessels or not self.sees(self.target):
            self.target = next(iter(self.combat_targets()), None)
        return self.target

    def cycle_target(self):
        targets = self.combat_targets()
        if not targets:
            self.target = None
            self.notify("NO CONTACTS IN SIGHT")
        elif self.target in targets:
            self.target = targets[(targets.index(self.target) + 1) % len(targets)]
        else:
            self.target = targets[0]

    def player_fire(self):
        """Fire at the target: a turn, SHOT_COST shield charge, and very loud. Returns hit or miss."""
        me = self.ship_center()
        target = self.current_target()
        if target is None:
            return self.notify("NO TARGET IN SIGHT")
        distance = math.dist(me, target.position)
        if self.sensors.blind(me) or self.sensors.blind(target.position):
            return self.notify("GLARE - NO LOCK", WARNING)
        if band(distance) is None:
            return self.notify(f"OUT OF RANGE - {exact_range(distance)}", WARNING)
        if not charged(self.player.ship):
            return self.notify("CAN'T FIRE - SHIELD CHARGE TOO LOW", WARNING)
        hit, to_shield, to_hull = fire(self.player.ship, target.ship, me, target.position, self.rng)
        self.shots.append(Shot(me, target.position, hit, OWN, pygame.time.get_ticks() + SHOT_MS))
        target.player_fix = (me, self.clock.now)
        if target.ship.hull <= 0:
            self.destroy(target)
        else:
            self.notify(f"HIT - {int(to_shield + to_hull)} DAMAGE" if hit else "MISS", NOTE)
            if hit:
                self.enemy_panel.hit(pygame.time.get_ticks())
        self.last_action = "fire"
        self.spend_turns(FIRE_TURNS)
        return hit

    def player_scan(self):
        """Scan the target: a turn, and from then on its intent shows above it."""
        me = self.ship_center()
        target = self.current_target()
        if target is None:
            return self.notify("NO TARGET IN SIGHT")
        if self.sensors.blind(me) or self.sensors.blind(target.position):
            return self.notify("GLARE - SCANNERS BLIND", WARNING)
        if math.dist(me, target.position) > SCAN_RANGE:
            return self.notify(f"TOO FAR TO SCAN - {exact_range(math.dist(me, target.position))}", WARNING)
        target.scanned = True
        self.notify(f"SCANNED {faction_name(target.sponsor).upper()} {target.kind.upper()}")
        self.last_action = "wait"
        self.spend_turns(SCAN_TURNS)

    def privateer_fire(self, privateer):
        """A privateer's shot at the player, by the same rules as yours."""
        me = self.ship_center()
        hit, to_shield, to_hull = fire(privateer.ship, self.player.ship, privateer.position, me, self.rng,
                                       privateer.power)
        self.shots.append(Shot(privateer.position, me, hit, privateer.colour, pygame.time.get_ticks() + SHOT_MS))
        if to_shield:
            self.shield_flash_until = pygame.time.get_ticks() + SHIELD_FLASH_MS
        if to_hull:
            self.notify(f"HULL HIT - {math.ceil(to_hull)}", DANGER)
        elif not hit:
            self.notify(f"{faction_name(privateer.sponsor).upper()} {privateer.kind.upper()} MISSED", NOTE)

    def destroy(self, privateer):
        """A privateer breaks up: it leaves a wreck worth salvaging, and standing moves."""
        self.vessels.remove(privateer)
        self.clock.remove(privateer)
        if self.target is privateer:
            self.target = None
        markets = self.world_state.markets_data()
        goods = set()
        for planet in self.selected_system.planets:
            if planet.planet_guild == privateer.sponsor:
                goods.update((markets.get(planet.id) or {}).get("goods") or {})
        if not goods:  # the sponsor's worlds have no market yet: carry anything that sells in Sol
            for market in markets.values():
                goods.update((market or {}).get("goods") or {})
        cargo, credits = roll_salvage(privateer.kind, goods, self.rng)
        wreck = Wreck(privateer, cargo, credits, self.remove_wreck)
        self.wrecks.append(wreck)
        self.clock.add(wreck)
        changes = record_kill(self.player, privateer.sponsor, privateer.kind, self.selected_system.politics.law)
        self.world_state.events.emit("privateer_destroyed", sponsor=privateer.sponsor, kind=privateer.kind,
                                     system=self.selected_system.id)
        self.notify(f"{faction_name(privateer.sponsor).upper()} {privateer.kind.upper()} DESTROYED", shake=True)
        self.notify(f"STANDING {changes}", NOTE)

    def remove_wreck(self, wreck):
        if wreck in self.wrecks:
            self.wrecks.remove(wreck)
            self.notify(f"{wreck.name.upper()} BROKE UP", NOTE)
        self.clock.remove(wreck)

    def salvage(self, wreck):
        """Take what fits from a wreck. Returns lines for the ship computer."""
        if wreck.empty():
            return ["Nothing left worth taking."]
        cargo = self.player.ship.cargo
        lines = []
        took = {}
        for good, quantity in list(wreck.cargo.items()):
            room = cargo.capacity - cargo.get_total_quantity()
            taken = min(quantity, room)
            if taken:
                cargo.add_item(good, taken)
                took[good] = taken
                lines.append(f"Took {taken} {item_name(good)} aboard.")
            if taken < quantity:
                lines.append(f"No room for {quantity - taken} more {item_name(good)}.")
                wreck.cargo[good] = quantity - taken
            else:
                del wreck.cargo[good]
        credits, wreck.credits = wreck.credits, 0
        if credits:
            self.player.currency += credits
            lines.append(f"Recovered ${credits}.")
        self.world_state.events.emit("salvaged", wreck=wreck.name, goods=took, credits=credits)
        for line in lines:
            self.notify(line.rstrip(".").upper(), NOTE)
        self.notify(f"SALVAGED {wreck.name.upper()}")
        return lines

    def sees(self, vessel):
        """Whether the player can sense `vessel` right now."""
        return self.sensors.sees(self.ship_center(), vessel.position, vessel.signature())

    def seen_by(self, vessel):
        """Whether `vessel` can sense the player right now."""
        return self.sensors.sees(vessel.position, self.ship_center(), self.player_signature())

    def area_ping(self):
        """Ping every direction: unknown ships in range show as bearings, and all of them hear you."""
        origin = self.ship_center()
        if self.sensors.blind(origin):
            return ["Glare: sensors are blind this deep in the sun."]
        turn = self.clock.now
        self.sensors.pulse(origin, pygame.time.get_ticks())
        heard = [v for v in self.vessels if self.sensors.in_ping_range(origin, v.position)]
        unknown = [v for v in heard if not self.sees(v) and self.sensors.catches(origin, v.position, v.signature())]
        in_sight = sum(1 for vessel in heard if self.sees(vessel))
        for vessel in heard:
            vessel.player_fix = (origin, turn)
        for vessel in unknown:
            self.sensors.mark(origin, vessel.position, turn, hostile=False)
        self.last_action = "ping"
        self.spend_turns(PING_TURNS)
        found = f"Area ping: {len(unknown)} unknown contact{'s' if len(unknown) != 1 else ''}"
        if in_sight:
            found += f", {in_sight} already in sight"
        lines = [found + "."]
        for vessel in sorted(unknown, key=lambda v: math.dist(origin, v.position)):
            lines.append(f"  Contact {compass(origin, vessel.position)}, about {range_label(math.dist(origin, vessel.position))}")
        lines.append("Every ship in range heard you." if heard else "Nothing answered.")
        return lines

    def vessel_ping(self, vessel):
        """Another ship pings. Your sensors pick up the pulse as it leaves, pointing back at the
        pinger; its wavefront then travels toward you and catches or misses you when it arrives."""
        self.sensors.enemy_pulse(vessel.position, self.clock.now, vessel)
        me = self.ship_center()
        if self.sensors.in_ping_range(vessel.position, me) and not self.sees(vessel):
            self.sensors.mark(me, vessel.position, self.clock.now, hostile=True)

    def incoming_pings(self):
        """Enemy rings still on their way to you, nearest arrival first, as (ring, distance)."""
        me = self.ship_center()
        pending = []
        for ring in self.sensors.rings:
            if not ring.hostile or ring.resolved:
                continue
            distance = math.dist(ring.origin, me)
            if distance <= PING_RANGE:
                pending.append((ring, distance))
        return sorted(pending, key=lambda item: item[1] - item[0].radius(0, self.clock.now))

    def resolve_pings(self):
        """Wavefronts that have reached you catch you or miss you, by how quiet you are now."""
        me = self.ship_center()
        for ring, distance in self.incoming_pings():
            if ring.radius(0, self.clock.now) < distance:
                continue
            ring.resolved = True
            if not self.sensors.catches(ring.origin, me, self.player_signature()):
                self.notify("PING MISSED YOU")
                self.ping_strip.landed(False, pygame.time.get_ticks())
                continue
            self.caught_by(ring.pinger)

    def caught_by(self, vessel):
        me = self.ship_center()
        vessel.player_fix = (me, self.clock.now)
        sponsor = getattr(vessel, "sponsor", None)
        who = faction_name(sponsor).upper() if sponsor else "A SHIP"
        self.ping_strip.landed(True, pygame.time.get_ticks())
        if sponsor and waves_by(self.player.reputation, sponsor):
            self.notify(f"PINGED BY {who} - THEY KNOW YOU")
        else:
            self.notify(f"PINGED - {who} HAS YOUR POSITION", WARNING)

    def ping_warning(self):
        """What the nearest incoming ping means for you, as a PingWarning, or None."""
        pending = self.incoming_pings()
        if not pending:
            return None
        ring, distance = pending[0]
        turns = max(1, math.ceil((distance - ring.radius(0, self.clock.now)) / PING_SPEED))
        limit = loudest_unfound(distance)
        if limit is None:
            advice = "TOO CLOSE TO DODGE"
        elif self.sensors.blind(self.ship_center()):
            advice = "THE GLARE HIDES YOU"
        else:
            advice = dodge_advice(limit, self.player.ship.cargo)
        return PingWarning(range_label(distance), compass(self.ship_center(), ring.origin), turns, advice)

    def hunted(self):
        return any(vessel.hunting() for vessel in self.vessels)

    def set_shield(self, up):
        self.player.ship.shield_up = up
        self.shield_changed_at = pygame.time.get_ticks()

    def shield_strength(self, now):
        """How solid the shell looks: charge, eased in or out after a toggle."""
        ship = self.player.ship
        fade = min(1.0, (now - self.shield_changed_at) / SHIELD_FADE_MS)
        shown = fade if ship.shield_up else 1 - fade
        return shown * ship.shield / ship.max_shield

    def hull_tint(self, now):
        """Damage tint step for the ship sprite; it flickers once the hull is critical."""
        ship = self.player.ship
        damage = 1 - ship.hull / ship.max_hull
        tint = min(TINT_LEVELS - 1, int(damage * TINT_LEVELS))
        if ship.hull < ship.max_hull * CRITICAL_HULL and (now // 250) % 2:
            tint -= 1
        return tint

    def burn_multiplier(self):
        multiplier = BOOST_BURN if self.boosting else 1.0
        if self.on_charted_ring():
            multiplier *= RING_BURN
        if self.in_atmosphere():
            multiplier *= ATMO_BURN
        return multiplier

    def on_charted_ring(self):
        sx, sy = self.ship_center()
        distance = math.hypot(sx - self.map_center_x, sy - self.map_center_y)
        for planet in self.selected_system.planets:
            if self.nav.is_charted(planet) and abs(distance - planet.orbit_radius) <= RING_BAND:
                return True
        return False

    def in_atmosphere(self):
        rect = self.ship_rect()
        for planet in self.selected_system.planets:
            if planet.contains(rect.center) and not self._in_approach(planet, rect):
                return True
        return False

    def _in_approach(self, body, rect):
        return any(rect.colliderect(approach) for approach in body.approach_rects())

    def check_collision(self):
        """The body whose access corridor the ship is in, if any. Where corridors overlap,
        somewhere to dock comes first, then a wreck with salvage left (ui.action_strip)."""
        rect = self.ship_rect()
        bodies = [*self.selected_system.planets, *self.selected_system.objects, *self.wrecks]
        return min((body for body in bodies if self._in_approach(body, rect)), key=corridor_rank, default=None)
    
    def open_scan_terminal(self, target):
        self.scan_terminal = ScanTerminal(target, self)
        self.scan_terminal.activate()

    def close_scan_terminal(self):
        self.scan_terminal = None

    def request_landing(self, planet):
        self.notify(f"DOCKING AT {planet.name.upper()}", NOTE)
        ship = self.player.ship
        ship.burn_fuel(amount=DOCK_FUEL)
        ship.shield = ship.max_shield  # station power tops the shield up while docked
        self.pending = Land(planet)
        self.close_scan_terminal()

    def notice(self, text):
        """A message for the player from outside this mode, such as "Game saved"."""
        self.notify(text.upper(), NOTE)

    def undock(self, body):
        """Back in flight after a stay at `body`, which is charted now that you've been there."""
        self.nav.chart(body.id)
        self.player.location.body = None

    def ping_targets(self):
        return [*self.selected_system.planets, *self.selected_system.objects]

    def ping(self, query):
        targets = self.ping_targets()
        if not query:
            return self.area_ping()

        matches = [body for body in targets if body.name.lower().startswith(query)]
        if not matches:
            return [f"No signal matching '{query}'."]
        if len(matches) > 1:
            return ["Which one? " + ", ".join(body.name for body in matches)]
        body = matches[0]
        if self.nav.is_charted(body):
            return [f"{body.name} is already charted."]

        origin = self.ship_center()
        if body.category == "planet":
            return self.nav.ping(body, origin)
        return self.nav.ping_fixed(body, origin, body.world_center())

    def update(self, events, dt):
        """One frame, `dt` seconds long. Returns a transition (modes.transitions) or None."""
        self.elapsed += dt
        # Enemy rings glide toward the turn clock rather than jumping a turn at a time.
        self.ring_turn = min(self.clock.now, self.ring_turn + max(0.0, self.clock.now - self.ring_turn) * min(1.0, dt * RING_EASE))
        self.handle_events(events, dt)
        transition, self.pending = self.pending, None
        return transition

    def handle_events(self, events, dt):
        if self.scan_terminal:
            for event in events:
                if not self.scan_terminal:
                    break
                if event.type == pygame.KEYDOWN:
                    self.scan_terminal.process_input(event)
                elif event.type == pygame.MOUSEWHEEL:
                    if event.y > 0:
                        self.scan_terminal.scroll_up()
                    elif event.y < 0:
                        self.scan_terminal.scroll_down()
            if self.scan_terminal:
                self.scan_terminal.update(dt)
            return

        for event in events:
            if event.type == pygame.KEYDOWN and event.key == pygame.K_e:
                self.open_scan_terminal(self.check_collision())
                return
            if event.type == pygame.KEYDOWN and event.key == SHIELD_KEY:
                self.set_shield(not self.player.ship.shield_up)
            if event.type == pygame.KEYDOWN and event.key == PING_KEY:
                lines = self.area_ping()
                self.notify(lines[0].upper())
                for contact in lines[1:-1]:  # each contact's bearing and range goes in the log
                    self.notify(contact.strip().upper(), NOTE)
            if event.type == pygame.KEYDOWN and event.key == TARGET_KEY:
                self.cycle_target()
            if event.type == pygame.KEYDOWN and event.key == FIRE_KEY:
                self.player_fire()
            if event.type == pygame.KEYDOWN and event.key == SCAN_KEY:
                self.player_scan()

        self.handle_continuous_updates()

    def handle_continuous_updates(self):
        self.handle_input()
    # Update logic for continuous effects like parallax
        self.parallax_offset_x, self.parallax_offset_y, self.parallax_velocity_x, self.parallax_velocity_y = update_parallax(
                        self.x_position, self.y_position, self.previous_x, self.previous_y,
                        self.parallax_offset_x, self.parallax_offset_y, self.parallax_velocity_x, self.parallax_velocity_y,
                        PARALLAX_FACTOR, PARALLAX_DAMPING_FACTOR, VELOCITY_THRESHOLD
                    )
        self.previous_x, self.previous_y = self.x_position, self.y_position
        self.animated_cargoship.update()
        self.camera.x = max(0, min(self.x_position * TILE_SIZE - SCREEN_WIDTH // 2, self.selected_system.MAP_WIDTH - SCREEN_WIDTH))
        self.camera.y = max(0, min(self.y_position * TILE_SIZE - SCREEN_HEIGHT // 2, self.selected_system.MAP_HEIGHT - SCREEN_HEIGHT))

    def draw(self, screen):
        # Draw logic specific to star system mode
        screen.fill((0, 0, 0))
        draw_stars(screen, self.white_stars, SCREEN_WIDTH, SCREEN_HEIGHT, (self.parallax_offset_x * 2, self.parallax_offset_y * 2))
        draw_stars(screen, self.purple_stars, SCREEN_WIDTH, SCREEN_HEIGHT, (self.parallax_offset_x * 3, self.parallax_offset_y * 3))
        draw_stars(screen, self.blue_stars, SCREEN_WIDTH, SCREEN_HEIGHT, (self.parallax_offset_x * 4, self.parallax_offset_y * 4))
        now = pygame.time.get_ticks()
        shake = self.shake.offset(now)  # the world shakes; the HUD over it doesn't
        self.camera.move_ip(shake)
        # Bodies go over the starfield: at flight scale they fill the screen.
        self.selected_system.draw(screen, self.camera)
        self.draw_beacons(screen)
        self.draw_candidate_arcs(screen)
        self.draw_nav_markers(screen)
        self.sensors.prune(self.clock.now, now)
        draw_sensor_overlay(screen, self.camera, self.sensors, self.clock.now, now, self.nav_font, self.ring_turn)
        for wreck in self.wrecks:
            centre = (wreck.position[0] - self.camera.x, wreck.position[1] - self.camera.y)
            if screen.get_rect().inflate(64, 64).collidepoint(centre):
                wreck.draw(screen, centre, self.nav_font)
        draw_contacts(screen, self.camera, [v for v in self.vessels if self.sees(v)],
                      self.sensors.rings, now, self.nav_font, self.ring_turn)
        self.draw_combat_marks(screen)
        ship_top_left = (
            self.x_position * TILE_SIZE - self.camera.x,
            self.y_position * TILE_SIZE - self.camera.y,
        )
        spaceship_frame, blit_pos = self.animated_cargoship.blit_position(
            self.current_direction, ship_top_left, self.hull_tint(now)
        )
        screen.blit(spaceship_frame, blit_pos)
        sprite_center = (ship_top_left[0] + self.frame_dimensions[0] // 2,
                         ship_top_left[1] + self.frame_dimensions[1] // 2)
        draw_shield(screen, sprite_center, self.shield_strength(now), now, now < self.shield_flash_until)
        self.shots = [shot for shot in self.shots if now <= shot.until_ms]
        draw_shots(screen, self.camera, self.shots, now, self.nav_font)
        self.camera.move_ip(-shake[0], -shake[1])
        self.draw_hud(screen, now)
        if self.scan_terminal:
            self.scan_terminal.display(screen)

    def draw_hud(self, screen, now):
        """Everything over the world: the edge glow first, so the panels stay crisp over it."""
        in_heat = self.selected_system.heat_at(self.ship_center()) > 0
        self.vignette.draw(screen, now, hold=HEAT_COLOUR if in_heat else None)
        self.ship_panel.draw(screen, self, now)
        self.enemy_panel.draw(screen, self, now)
        if not self.scan_terminal:
            self.action_strip.draw(screen, self, now, ATMO_BURN)
        draw_log(screen, self.events, now)
        self.ping_strip.draw(screen, self.ping_warning(), now)
        self.banner.draw(screen, now)

    def draw_combat_marks(self, screen):
        """Intent glyphs over scanned ships you can sense, and a bracket on the target."""
        target = self.current_target()
        for vessel in self.vessels:
            if not vessel.armed or not self.sees(vessel):
                continue
            centre = (vessel.position[0] - self.camera.x, vessel.position[1] - self.camera.y)
            if not screen.get_rect().collidepoint(centre):
                continue
            if vessel is target:
                draw_bracket(screen, centre, TARGET_COLOR)
            if vessel.scanned:
                draw_intent(screen, centre, vessel.intent, vessel.colour, self.nav_font)

    def draw_beacons(self, screen):
        """Charted starports and station bays. Uncharted pads stay dark until a ping locks."""
        blink_on = (pygame.time.get_ticks() // 350) % 2 == 0
        color = BEACON_COLOR if blink_on else BEACON_DIM
        points = []
        for planet in self.selected_system.planets:
            if self.nav.is_charted(planet):
                points.extend(planet.beacon_points())
        for obj in self.selected_system.objects:
            if self.nav.is_charted(obj):
                points.extend(obj.access_points())
        for x, y in points:
            sx, sy = int(x - self.camera.x), int(y - self.camera.y)
            if not screen.get_rect().collidepoint(sx, sy):
                continue
            pygame.draw.circle(screen, color, (sx, sy), 7, 1)
            pygame.draw.circle(screen, color, (sx, sy), 2)

    def draw_candidate_arcs(self, screen):
        """Highlight the parts of each uncharted orbit where pings say the planet could be."""
        for planet in self.selected_system.planets:
            if self.nav.is_charted(planet):
                continue
            for run in self.nav.candidate_runs(planet):
                points = []
                for index in run:
                    x, y = self.nav.orbit_point(planet, index)
                    points.append((x - self.camera.x, y - self.camera.y))
                if len(points) > 1:
                    pygame.draw.lines(screen, CANDIDATE_ARC_COLOR, False, points, 3)
                else:
                    pygame.draw.circle(screen, CANDIDATE_ARC_COLOR, points[0], 3)

    def draw_nav_markers(self, screen):
        """Edge-of-screen arrows pointing at charted planets and stations."""
        screen_rect = screen.get_rect()
        half_w = SCREEN_WIDTH / 2 - NAV_MARKER_MARGIN
        half_h = SCREEN_HEIGHT / 2 - NAV_MARKER_MARGIN
        center_x, center_y = SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2
        markers = list(self.selected_system.planets)
        markers.extend(obj for obj in self.selected_system.objects if self.nav.is_charted(obj))
        for body in markers:
            if not self.nav.is_charted(body):
                continue
            wx, wy = body.world_center()
            sx = wx - self.camera.x
            sy = wy - self.camera.y
            if screen_rect.collidepoint(sx, sy):
                continue
            dx, dy = sx - center_x, sy - center_y
            scale = min(half_w / abs(dx) if dx else math.inf, half_h / abs(dy) if dy else math.inf)
            mx, my = center_x + dx * scale, center_y + dy * scale
            angle = math.atan2(dy, dx)
            tip = (mx + math.cos(angle) * 10, my + math.sin(angle) * 10)
            left = (mx + math.cos(angle + 2.5) * 8, my + math.sin(angle + 2.5) * 8)
            right = (mx + math.cos(angle - 2.5) * 8, my + math.sin(angle - 2.5) * 8)
            pygame.draw.polygon(screen, NAV_MARKER_COLOR, [tip, left, right])
            label = self.nav_font.render(body.name, True, NAV_MARKER_COLOR)
            label_rect = label.get_rect(center=(mx - math.cos(angle) * 28, my - math.sin(angle) * 18))
            screen.blit(label, label_rect.clamp(screen_rect))


def dodge_advice(limit, cargo):
    """The least restrictive way to fly that stays under `limit`, given what's in the hold."""
    fill = cargo.get_total_quantity() / cargo.capacity
    options = (
        ("SHIELD UP, NO BOOST", signature(True, True, False, fill)),
        ("HOLD STILL, SHIELD UP", signature(False, True, False, fill)),
        ("SHIELD DOWN, NO BOOST", signature(True, False, False, fill)),
        ("HOLD STILL, SHIELD DOWN", signature(False, False, False, fill)),
    )
    for advice, loudness in options:
        if loudness < limit:
            #return f"DODGE: {advice} (SIGNAL UNDER {int(limit)})"
            return f"KEEP SIGNAL UNDER {int(limit)}"
    return f"CAN'T DODGE WITH THIS CARGO (SIGNAL UNDER {int(limit)})"


def exact_range(distance):
    """Weapon and scan ranges to the metre; ping ranges stay rough (sensors.range_label)."""
    return f"{int(distance)} m"
