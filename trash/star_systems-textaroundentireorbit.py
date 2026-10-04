## This file handles the generation of star_systems.

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
    
        font = pygame.font.Font("space/assets/fonts/OfficeCodePro-Light.ttf", 14)
    
        # Draw orbits
        for planet in self.planets:
            orbit_radius = planet.orbit_radius
            pygame.draw.circle(self.map_surface, (255, 255, 255), (self.map_center_x, self.map_center_y), orbit_radius, 1)
    
            # Check if orbit is visible and draw text
            if self.is_orbit_visible(orbit_radius, camera):
                self.draw_planet_name(screen, camera, self.map_center_x, self.map_center_y, orbit_radius, planet.name, font)
    
        # Draw planets
        for planet in self.planets:
            planet.draw(self.map_surface)
    
    def is_orbit_visible(self, orbit_radius, camera):
        # Check if the orbit is within the camera's visible area
        camera_rect = pygame.Rect(camera.x, camera.y, camera.width, camera.height)
        orbit_rect = pygame.Rect(self.map_center_x - orbit_radius, self.map_center_y - orbit_radius, 2 * orbit_radius, 2 * orbit_radius)
        return camera_rect.colliderect(orbit_rect)

    def calculate_text_positions(self, orbit_radius, camera, center_x, center_y, text):
        positions = []
        for i, char in enumerate(text):
            angle = 360 * i / len(text)
            angle_rad = math.radians(angle)
            x = center_x + orbit_radius * math.cos(angle_rad)
            y = center_y + orbit_radius * math.sin(angle_rad)

            # Adjust position relative to camera
            text_x = x - camera.x
            text_y = y - camera.y
            positions.append((text_x, text_y))
        return positions
    
    def draw_planet_name(self, screen, camera, center_x, center_y, orbit_radius, text, font):
        positions = self.calculate_text_positions(orbit_radius, camera, center_x, center_y, text)

        for i, (x, y) in enumerate(positions):
            char_surface = font.render(text[i], True, (255, 255, 255))
            screen.blit(char_surface, (x, y))


# Usage example
# sol_system = StarSystem('space/star_systems/sol.json')
# sol_system.draw(screen, camera)
