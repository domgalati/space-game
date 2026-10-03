import json
import math
import random

import pygame

from util.config import resolve_game_path

# Corridor around the painted starport. Radius, so the ship has to be on that rim.
APPROACH_RADIUS = 64
# Style A disks paint the pad on the lit rim (same vector the glyph generator uses).
_DOCK_LEN = math.hypot(0.62, 0.48)
DOCK_XY = (-0.62 / _DOCK_LEN * 0.84, -0.48 / _DOCK_LEN * 0.84)


class Planet:
    def __init__(self, name, planet_type, planet_guild, image_path, orbit_radius, angle, center_x, center_y,start_pos=(0, 0)):
        self.name = name
        self.planet_type = planet_type
        self.planet_guild = planet_guild
        self.image = pygame.image.load(image_path)
        self.orbit_radius = orbit_radius
        self.angle = angle
        self.position = self.calculate_position(center_x, center_y)
        self.start_pos = start_pos

    def calculate_position(self, center_x, center_y):
        x = center_x + int(self.orbit_radius * math.cos(self.angle))
        y = center_y + int(self.orbit_radius * math.sin(self.angle))
        return x, y

    def get_rect(self):
        # Assuming the image's center is at the planet's position
        rect_x = self.position[0] - self.image.get_width() // 2
        rect_y = self.position[1] - self.image.get_height() // 2
        return pygame.Rect(rect_x, rect_y, self.image.get_width(), self.image.get_height())

    def beacon_points(self):
        """World position of the starport painted on the disk."""
        half = self.image.get_width() / 2
        return [(
            self.position[0] + DOCK_XY[0] * half,
            self.position[1] + DOCK_XY[1] * half,
        )]

    def approach_rects(self):
        rects = []
        for x, y in self.beacon_points():
            rects.append(pygame.Rect(x - APPROACH_RADIUS, y - APPROACH_RADIUS,
                                     APPROACH_RADIUS * 2, APPROACH_RADIUS * 2))
        return rects

    def draw(self, surface, camera):
        if not camera.colliderect(self.get_rect()):
            return
        adjusted_pos = (
            self.position[0] - self.image.get_width() // 2 - camera.x,
            self.position[1] - self.image.get_height() // 2 - camera.y,
        )
        surface.blit(self.image, adjusted_pos)

def generate_planets(json_path, center_x, center_y):
    # random.seed(seed)
    orbits = []

    # Load data from JSON file
    with open(resolve_game_path(json_path), "r") as file:
        data = json.load(file)
        seed = data['seed']
        planet_data = data['planets']
        random.seed(seed)

    planets = []
    min_orbit_radius = 500
    max_orbit_radius = 5760
    min_distance_between_orbits = 500
    max_distance_between_orbits = 1000
    last_orbit_radius = min_orbit_radius

    for data in planet_data:
        if last_orbit_radius > max_orbit_radius:
            break

        orbit_radius = last_orbit_radius + random.randint(min_distance_between_orbits, max_distance_between_orbits)
        angle = random.uniform(0, 2 * math.pi)

        planet = Planet(data['name'], data['type'], data['image_path'], orbit_radius, angle, center_x, center_y)
        planets.append(planet)
        orbits.append(orbit_radius)
        last_orbit_radius = orbit_radius

    return planets, orbits