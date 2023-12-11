import os
import json
import random
import math
import pygame
from planet import Planet
from config import SCREEN_WIDTH, SCREEN_HEIGHT

class StarSystem:
    def __init__(self, json_path):
        self.MAP_WIDTH = SCREEN_WIDTH * 24
        self.MAP_HEIGHT = SCREEN_HEIGHT * 24
        # Calculate center of the map as class attributes
        self.map_center_x = self.MAP_WIDTH // 2
        self.map_center_y = self.MAP_HEIGHT // 2        
        self.map_surface = None
        self.planets = []
        self.orbits = []
        self.load_system(json_path)

    def load_system(self, json_path):
        with open(json_path, 'r') as file:
            data = json.load(file)
            seed = data['seed']
            planet_data = data['planets']
            random.seed(seed)

            self.map_surface = pygame.Surface((self.MAP_WIDTH, self.MAP_HEIGHT)) # Create a surface for the map
            self.generate_planets(planet_data)

    def generate_planets(self, planet_data):
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

            planet = Planet(data['name'], data['type'], data['image_path'], orbit_radius, angle, self.map_center_x, self.map_center_y)
            self.planets.append(planet)
            self.orbits.append(orbit_radius)
            last_orbit_radius = orbit_radius

    def draw(self, screen, camera):
        screen.blit(self.map_surface, (0, 0), camera)
        for orbit_radius in self.orbits:
            pygame.draw.circle(self.map_surface, (255, 255, 255), (self.map_center_x, self.map_center_y), orbit_radius, 1)
        for planet in self.planets:
            planet.draw(self.map_surface)

# Usage example
# sol_system = StarSystem('space/star_systems/sol.json')
# sol_system.draw(screen, camera)
