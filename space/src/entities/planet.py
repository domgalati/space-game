import pygame
import math
import random
import json


class Planet:
    def __init__(self, name, planet_type, image_path, orbit_radius, angle, center_x, center_y):
        self.name = name
        self.planet_type = planet_type
        self.image = pygame.image.load(image_path)
        self.orbit_radius = orbit_radius
        self.angle = angle
        self.position = self.calculate_position(center_x, center_y)

    def calculate_position(self, center_x, center_y):
        x = center_x + int(self.orbit_radius * math.cos(self.angle))
        y = center_y + int(self.orbit_radius * math.sin(self.angle))
        return x, y

    def get_rect(self):
        # Assuming the image's center is at the planet's position
        rect_x = self.position[0] - self.image.get_width() // 2
        rect_y = self.position[1] - self.image.get_height() // 2
        return pygame.Rect(rect_x, rect_y, self.image.get_width(), self.image.get_height())

    def draw(self, surface):
        adjusted_pos = (self.position[0] - self.image.get_width() // 2, self.position[1] - self.image.get_height() // 2)
        surface.blit(self.image, adjusted_pos)

def generate_planets(json_path, center_x, center_y):
    # random.seed(seed)
    orbits = []

    # Load data from JSON file
    with open(json_path, 'r') as file:
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