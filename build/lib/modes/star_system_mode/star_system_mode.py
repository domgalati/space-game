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

CANDIDATE_ARC_COLOR = (255, 191, 0)
NAV_MARKER_COLOR = (120, 220, 140)
NAV_MARKER_MARGIN = 28
RESERVE_SLOWDOWN = 5  # move cooldown multiplier once the tank is empty
LOW_FUEL = 20
HUD_COLOR = (200, 210, 220)
LOW_FUEL_COLOR = (232, 150, 64)
RESERVE_COLOR = (230, 80, 70)

class StarSystemMode:
    def __init__(self, player, starsystem): 
        self.selected_system = StarSystem(resolve_game_path(f"space/star_systems/{starsystem}.json"))
        self.input_handler = InputHandler(self.selected_system, self)  # Instantiate InputHandler
        self.cruise_cooldown = self.input_handler.movement_cooldown
        self.grid_size = (self.selected_system.MAP_WIDTH // TILE_SIZE, self.selected_system.MAP_HEIGHT // TILE_SIZE)
        self.white_stars, self.purple_stars, self.blue_stars = initialize_stars(SCREEN_WIDTH, SCREEN_HEIGHT)
        self.map_center_x = self.selected_system.MAP_WIDTH // 2
        self.map_center_y = self.selected_system.MAP_HEIGHT // 2
        self.cargo_sheet = 'space/assets/img/cargo6frame.png'
        self.frame_dimensions = (48, 48)
        self.num_frames = 6
        self.animated_cargoship = AnimatedSprite(
            resolve_game_path(self.cargo_sheet), self.frame_dimensions, self.num_frames
        )
        self.current_direction = "southeast"
        self.x_position = self.map_center_x // TILE_SIZE
        self.y_position = self.map_center_y // TILE_SIZE
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

    def handle_input(self):
        # Handle input specific to this mode
        ship = self.player.ship
        slowdown = RESERVE_SLOWDOWN if ship.on_reserve else 1
        self.input_handler.movement_cooldown = self.cruise_cooldown * slowdown
        before = (self.x_position, self.y_position)
        self.x_position, self.y_position = self.input_handler.handle_movement(self.x_position, self.y_position, self.grid_size)
        if (self.x_position, self.y_position) != before:
            ship.burn_fuel()
        new_direction = determine_direction(self.x_position, self.y_position, self.previous_x, self.previous_y)
        if new_direction:
            self.current_direction = new_direction

    def check_collision(self):
        ship_rect = pygame.Rect(self.x_position * TILE_SIZE, self.y_position * TILE_SIZE, TILE_SIZE, TILE_SIZE)
        for planet in self.selected_system.planets:
            if ship_rect.colliderect(planet.get_rect()):
                return planet
        for obj in self.selected_system.objects:
            if ship_rect.colliderect(obj.get_rect()):
                return obj
        return None
    
    def open_scan_terminal(self, target):
        self.scan_terminal = ScanTerminal(target, self)
        self.scan_terminal.activate()

    def close_scan_terminal(self):
        self.scan_terminal = None

    def request_landing(self, planet):
        self.selected_planet = planet
        self.landing_requested = True
        self.close_scan_terminal()

    def ping(self, query):
        uncharted = [p for p in self.selected_system.planets if not self.nav.is_charted(p)]
        if not query:
            if not uncharted:
                return ["All planets in this system are charted."]
            return ["Usage: ping <planet>", "Uncharted: " + ", ".join(p.name for p in uncharted)]

        matches = [p for p in self.selected_system.planets if p.name.lower().startswith(query)]
        if not matches:
            return [f"No signal matching '{query}'."]
        if len(matches) > 1:
            return ["Which one? " + ", ".join(p.name for p in matches)]
        planet = matches[0]
        if self.nav.is_charted(planet):
            return [f"{planet.name} is already charted."]

        ship_center = (
            self.x_position * TILE_SIZE + TILE_SIZE // 2,
            self.y_position * TILE_SIZE + TILE_SIZE // 2,
        )
        return self.nav.ping(planet, ship_center)

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
        self.selected_system.draw(screen, self.camera)
        draw_stars(screen, self.white_stars, SCREEN_WIDTH, SCREEN_HEIGHT, (self.parallax_offset_x * 2, self.parallax_offset_y * 2))
        draw_stars(screen, self.purple_stars, SCREEN_WIDTH, SCREEN_HEIGHT, (self.parallax_offset_x * 3, self.parallax_offset_y * 3))
        draw_stars(screen, self.blue_stars, SCREEN_WIDTH, SCREEN_HEIGHT, (self.parallax_offset_x * 4, self.parallax_offset_y * 4))
        self.draw_candidate_arcs(screen)
        self.draw_nav_markers(screen)
        spaceship_frame = self.animated_cargoship.get_frame(self.current_direction)
        screen.blit(spaceship_frame, (self.x_position * TILE_SIZE - self.camera.x, self.y_position * TILE_SIZE - self.camera.y))
        self.draw_hud(screen)
        
        if self.scan_terminal:
            self.scan_terminal.display(screen)
        elif self.check_collision():
            font = pygame.font.Font(None, 36)
            text_surface = font.render("[E] Scan", True, (255, 255, 255))
            screen.blit(text_surface, (SCREEN_WIDTH // 2 - text_surface.get_width() // 2, SCREEN_HEIGHT // 2))
        
        print(f"camera: {self.camera}")

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
            lines.insert(0, (f"FUEL {int(ship.fuel)}/{ship.max_fuel}", color))
        y = 12
        for text, color in lines:
            surface = self.nav_font.render(text, True, color)
            screen.blit(surface, (12, y))
            y += surface.get_height() + 2

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
        """Edge-of-screen arrows pointing at charted planets that are off screen."""
        screen_rect = screen.get_rect()
        half_w = SCREEN_WIDTH / 2 - NAV_MARKER_MARGIN
        half_h = SCREEN_HEIGHT / 2 - NAV_MARKER_MARGIN
        center_x, center_y = SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2
        for planet in self.selected_system.planets:
            if not self.nav.is_charted(planet):
                continue
            sx = planet.position[0] - self.camera.x
            sy = planet.position[1] - self.camera.y
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
            label = self.nav_font.render(planet.name, True, NAV_MARKER_COLOR)
            label_rect = label.get_rect(center=(mx - math.cos(angle) * 28, my - math.sin(angle) * 18))
            screen.blit(label, label_rect.clamp(screen_rect))