## This file handles the generation of star_systems.
import json
import random
import math
import pygame
from entities.planet import Planet
from entities.object import SpaceObject
from util.config import SCREEN_WIDTH, SCREEN_HEIGHT

class StarSystem:
    def __init__(self, json_path):
        self.MAP_WIDTH = SCREEN_WIDTH * 24
        self.MAP_HEIGHT = SCREEN_HEIGHT * 24
        # Calculate center of the map as class attributes
        self.map_center_x = self.MAP_WIDTH // 2
        self.map_center_y = self.MAP_HEIGHT // 2        
        self.map_surface = None
        self.planets = []
        self.objects = []
        self.orbits = []
        self.load_system(json_path)

    def load_system(self, json_path):
        with open(json_path, 'r') as file:
            data = json.load(file)
            seed = data['seed']
            planet_data = data['planets']
            object_data = data.get('objects', [])
            random.seed(seed)

            self.map_surface = pygame.Surface((self.MAP_WIDTH, self.MAP_HEIGHT)) # Create a surface for the map
            self.generate_planets(planet_data)
            self.generate_objects(object_data)

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
            
            start_pos = data.get('start_pos', (0, 0))
            planet = Planet(data['name'], data['type'], data['guild'], data['image_path'], orbit_radius, angle, self.map_center_x, self.map_center_y, start_pos)
            self.planets.append(planet)
            self.orbits.append(orbit_radius)
            last_orbit_radius = orbit_radius

    def generate_objects(self, object_data):
        self.objects = []
        for data in object_data:
            obj = SpaceObject(data['name'], data['type'], data['image_path'], data['x'], data['y'])
            self.objects.append(obj)

    def draw(self, screen, camera):
        screen.blit(self.map_surface, (0, 0), camera)
        font = pygame.font.Font("space/assets/fonts/OfficeCodePro-Light.ttf", 14)

        for obj in self.objects:
            obj.draw(self.map_surface, camera)

        for planet in self.planets:
            orbit_radius = planet.orbit_radius
            pygame.draw.circle(self.map_surface, (255, 255, 255), (self.map_center_x, self.map_center_y), orbit_radius, 1)

            if self.is_orbit_visible(orbit_radius, camera):
                self.draw_planet_name_along_orbit(planet, font, screen, camera, orbit_radius)

            planet.draw(self.map_surface)

    
    def draw_planet_name_along_orbit(self, planet, font, screen, camera, orbit_radius, segment_start_ratio=0.25, segment_end_ratio=0.50):
        name = planet.name
        char_spacing = 2  # Space between characters
        name_length = len(name) * char_spacing
        visible_segments = self.get_visible_segments(orbit_radius, camera, name_length)

        if not visible_segments:
            return

        raw_start_angle, raw_end_angle = visible_segments[0]  # Consider only the first visible segment
        segment_angle_range = raw_end_angle - raw_start_angle

        #print(f"raw_start_angle:{raw_start_angle}, raw_end_angle:{raw_end_angle}") ##Debug
        if raw_start_angle < 180:
            name = name[::-1]  # Reverse the name

        # Calculate actual start and end angles based on the provided ratios
        start_angle = raw_start_angle + segment_angle_range * segment_start_ratio
        end_angle = raw_start_angle + segment_angle_range * segment_end_ratio

        for i, char in enumerate(name):
            angle = start_angle + (end_angle - start_angle) * i / (len(name) - 1)
            angle_rad = math.radians(angle)

            x = self.map_center_x + orbit_radius * math.cos(angle_rad) - camera.x
            y = self.map_center_y + orbit_radius * math.sin(angle_rad) - camera.y

            char_surface = font.render(char, True, (255, 255, 255))
            char_rect = char_surface.get_rect(center=(x + 10, y + 10))
            screen.blit(char_surface, char_rect)
        
    def is_orbit_visible(self, orbit_radius, camera):
        # Check if the orbit is within the camera's visible area
        camera_rect = pygame.Rect(camera.x, camera.y, camera.width, camera.height)
        orbit_rect = pygame.Rect(self.map_center_x - orbit_radius, self.map_center_y - orbit_radius, 2 * orbit_radius, 2 * orbit_radius)
        return camera_rect.colliderect(orbit_rect)

    def get_visible_segments(self, orbit_radius, camera, name_length):
        visible_segments = []
        start_angle = None
        for angle in range(0, 360, 1):  # Check every degree for more precision
            angle_rad = math.radians(angle)
            x = self.map_center_x + orbit_radius * math.cos(angle_rad)
            y = self.map_center_y + orbit_radius * math.sin(angle_rad) + 100

            if camera.x <= x <= camera.x + camera.width and camera.y <= y <= camera.y + camera.height:
                if start_angle is None:
                    start_angle = angle
            else:
                if start_angle is not None:
                    end_angle = angle
                    if end_angle - start_angle >= self.calculate_angle_length(orbit_radius, name_length):
                        visible_segments.append((start_angle, end_angle))
                    start_angle = None

        if start_angle is not None:
            end_angle = 360
            if end_angle - start_angle >= self.calculate_angle_length(orbit_radius, name_length):
                visible_segments.append((start_angle, end_angle))

        return visible_segments

    def calculate_angle_length(self, orbit_radius, length):
        return math.degrees(length / orbit_radius)



# Usage example
# sol_system = StarSystem('space/star_systems/sol.json')
# sol_system.draw(screen, camera)
