# This file handles the main loop when the player is traversing a star system

import math

import pygame
from util.config import SCREEN_WIDTH, SCREEN_HEIGHT, TILE_SIZE, resolve_game_path
from .input_handler import InputHandler, determine_direction, update_parallax
from .nightsky import initialize_stars, draw_stars, PARALLAX_FACTOR, PARALLAX_DAMPING_FACTOR, VELOCITY_THRESHOLD
from util.sprite_animation import AnimatedSprite
from .nav_charts import NavCharts
from .scan_terminal import ScanTerminal
from .star_systems import StarSystem
from util.economy.news_feed import NewsFeed
from world.world_state import WorldState
from entities.player import DOCK_FUEL

CANDIDATE_ARC_COLOR = (255, 191, 0)
NAV_MARKER_COLOR = (120, 220, 140)
NAV_MARKER_MARGIN = 28
RESERVE_SLOWDOWN = 5  # move cooldown multiplier once the tank is empty
BOOST_SCALE = 0.5  # hold shift: twice as fast, twice the burn
BOOST_BURN = 2.0
RING_BAND = 160  # px from a charted orbit that counts as riding the ring
RING_BURN = 0.5
ATMO_BURN = 2.0
LOW_FUEL = 20
BEACON_COLOR = (0, 196, 32)
BEACON_DIM = (207, 192, 65)
HUD_COLOR = (200, 210, 220)
HUD_BACKING = (0, 0, 0, 170)
LOW_FUEL_COLOR = (232, 150, 64)
RESERVE_COLOR = (230, 80, 70)

class StarSystemMode:
    def __init__(self, player, starsystem, world_state=None):
        self.world_state = world_state or WorldState()
        self.news_feed = NewsFeed(self.world_state)
        self.selected_system = StarSystem(resolve_game_path(f"space/star_systems/{starsystem}.json"))
        self.input_handler = InputHandler(self.selected_system, self)  # Instantiate InputHandler
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
        spawn_x, spawn_y = self.selected_system.spawn_point()
        self.x_position = int(spawn_x) // TILE_SIZE
        self.y_position = int(spawn_y) // TILE_SIZE
        self.previous_x, self.previous_y = self.x_position, self.y_position
        self.parallax_offset_x, self.parallax_offset_y = 0, 0
        self.parallax_velocity_x, self.parallax_velocity_y = 0, 0
        self.camera = pygame.Rect(0, 0, SCREEN_WIDTH, SCREEN_HEIGHT)
        self.landing_requested = False
        self.player = player
        self.selected_planet = None
        self.scan_terminal = None
        self.last_tick = pygame.time.get_ticks()
        self.nav = NavCharts((self.map_center_x, self.map_center_y), player.charted_planets)
        self.nav_font = pygame.font.Font(resolve_game_path("space/assets/fonts/OfficeCodePro-Light.ttf"), 14)
        self.boosting = False

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
        self.x_position, self.y_position = self.input_handler.handle_movement(self.x_position, self.y_position, self.grid_size)
        if (self.x_position, self.y_position) != before:
            ship.burn_fuel(multiplier=self.burn_multiplier())
        new_direction = determine_direction(self.x_position, self.y_position, self.previous_x, self.previous_y)
        if new_direction:
            self.current_direction = new_direction

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
        """The body whose access corridor the ship is in, if any."""
        rect = self.ship_rect()
        for planet in self.selected_system.planets:
            if self._in_approach(planet, rect):
                return planet
        for obj in self.selected_system.objects:
            if self._in_approach(obj, rect):
                return obj
        return None
    
    def open_scan_terminal(self, target):
        self.scan_terminal = ScanTerminal(target, self)
        self.scan_terminal.activate()

    def close_scan_terminal(self):
        self.scan_terminal = None

    def request_landing(self, planet):
        self.player.ship.burn_fuel(amount=DOCK_FUEL)
        self.selected_planet = planet
        self.landing_requested = True
        self.close_scan_terminal()

    def ping_targets(self):
        return [*self.selected_system.planets, *self.selected_system.objects]

    def ping(self, query):
        targets = self.ping_targets()
        uncharted = [body for body in targets if not self.nav.is_charted(body)]
        if not query:
            if not uncharted:
                return ["All contacts in this system are charted."]
            return ["Usage: ping <name>", "Uncharted: " + ", ".join(body.name for body in uncharted)]

        matches = [body for body in targets if body.name.lower().startswith(query)]
        if not matches:
            return [f"No signal matching '{query}'."]
        if len(matches) > 1:
            return ["Which one? " + ", ".join(body.name for body in matches)]
        body = matches[0]
        if self.nav.is_charted(body):
            return [f"{body.name} is already charted."]

        origin = self.ship_center()
        if hasattr(body, "orbit_radius"):
            return self.nav.ping(body, origin)
        return self.nav.ping_fixed(body, origin, body.world_center())

    def get_selected_planet(self):
        return self.selected_planet
    
    def get_player(self):
        # Assuming self.player is an attribute holding the player's state
        return self.player

    def update(self, events):
        now = pygame.time.get_ticks()
        dt = (now - self.last_tick) / 1000.0
        self.last_tick = now

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
        # Bodies go over the starfield: at flight scale they fill the screen.
        self.selected_system.draw(screen, self.camera)
        self.draw_beacons(screen)
        self.draw_candidate_arcs(screen)
        self.draw_nav_markers(screen)
        ship_top_left = (
            self.x_position * TILE_SIZE - self.camera.x,
            self.y_position * TILE_SIZE - self.camera.y,
        )
        spaceship_frame, blit_pos = self.animated_cargoship.blit_position(
            self.current_direction, ship_top_left
        )
        screen.blit(spaceship_frame, blit_pos)
        self.draw_hud(screen)
        
        if self.scan_terminal:
            self.scan_terminal.display(screen)
        elif self.check_collision():
            font = pygame.font.Font(None, 36)
            text_surface = font.render("[E] Scan", True, (255, 255, 255))
            screen.blit(text_surface, (SCREEN_WIDTH // 2 - text_surface.get_width() // 2, SCREEN_HEIGHT // 2))
        elif self.in_atmosphere():
            font = pygame.font.Font(None, 36)
            text_surface = font.render("ATMOSPHERE", True, (232, 150, 64))
            screen.blit(text_surface, (SCREEN_WIDTH // 2 - text_surface.get_width() // 2, SCREEN_HEIGHT // 2))

    def draw_hud(self, screen):
        ship = self.player.ship
        cargo = ship.cargo
        lines = [
            (f"CREDITS ${self.player.currency}", HUD_COLOR),
            (f"CARGO {cargo.get_total_quantity()}/{cargo.capacity}", HUD_COLOR),
        ]
        if ship.on_reserve:
            lines.insert(0, ("FUEL EMPTY - RESERVE THRUSTERS", RESERVE_COLOR))
        else:
            color = LOW_FUEL_COLOR if ship.fuel < LOW_FUEL else HUD_COLOR
            label = f"FUEL {int(ship.fuel)}/{ship.max_fuel}"
            if self.boosting:
                label += "  BOOST"
            elif self.on_charted_ring():
                label += "  RING"
            lines.insert(0, (label, color))
        surfaces = [self.nav_font.render(text, True, color) for text, color in lines]
        # Planets and the sun can fill the screen, so the readout sits on a dark plate.
        width = max(surface.get_width() for surface in surfaces) + 12
        height = sum(surface.get_height() + 2 for surface in surfaces) + 8
        backing = pygame.Surface((width, height), pygame.SRCALPHA)
        backing.fill(HUD_BACKING)
        screen.blit(backing, (6, 8))
        y = 12
        for surface in surfaces:
            screen.blit(surface, (12, y))
            y += surface.get_height() + 2

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
            if hasattr(body, "world_center"):
                wx, wy = body.world_center()
            else:
                wx, wy = body.position
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