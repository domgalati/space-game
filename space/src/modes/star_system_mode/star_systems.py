## This file handles the generation of star_systems.
import json
import random
import math
import pygame
from entities.planet import Planet
from entities.object import SpaceObject
from util.config import resolve_game_path
from util.images import load_image
from world.atlas import body_id
from world.factions import LAW

# Logical system is large enough for multi-thousand-pixel orbit gaps.
# Bodies are drawn straight to the screen, so this does not allocate a bitmap.
MAP_WIDTH = 86000
MAP_HEIGHT = 86000
MIN_ORBIT_RADIUS = 2200
MIN_ORBIT_GAP = 3200
MAX_ORBIT_GAP = 4200
ORBIT_COLOR = (21, 83, 82)
SUN_IMAGE = "space/assets/img/planets/Sun.png"
SUN_RADIUS = 1700  # the glyph disk in Sun.png; its corona dots reach a little past it
STATION_ANGLE = 0.4  # radians from the sun; the art is lit from the upper left, so the sun sits there
STATION_GAP = 450  # open space between the sun's disk and the station image
SPAWN_BELOW_BAY = 280  # a new run starts just outside the bay corridor, bay in view
HEAT_START = 0.6  # fraction of SUN_RADIUS where solar heat begins; the outer sun is safe
HEAT_MAX = 8  # damage per turn at the very core
PATROL_RADIUS = 2500  # privateers break off this close to Assembly worlds and stations

class StarSystem:
    def __init__(self, json_path):
        self.id = None
        self.name = None
        self.MAP_WIDTH = MAP_WIDTH
        self.MAP_HEIGHT = MAP_HEIGHT
        # Calculate center of the map as class attributes
        self.map_center_x = self.MAP_WIDTH // 2
        self.map_center_y = self.MAP_HEIGHT // 2
        self.sun_image = load_image(resolve_game_path(SUN_IMAGE))
        self.planets = []
        self.objects = []
        self.orbits = []
        self.name_font = None  # loaded on first draw
        self.load_system(json_path)

    def load_system(self, json_path):
        with open(resolve_game_path(json_path), 'r') as file:
            data = json.load(file)
            self.id = data['id']
            self.name = data.get('name', self.id)
            seed = data['seed']
            planet_data = data['planets']
            object_data = data.get('objects', [])
            random.seed(seed)

            self.generate_planets(planet_data)
            self.generate_objects(object_data)

    def generate_planets(self, planet_data):
        last_orbit_radius = MIN_ORBIT_RADIUS

        for data in planet_data:
            orbit_radius = last_orbit_radius + random.randint(MIN_ORBIT_GAP, MAX_ORBIT_GAP)
            angle = random.uniform(0, 2 * math.pi)
            
            start_pos = data.get('start_pos', (0, 0))
            planet = Planet(
                body_id(self.id, data['id']),
                data['name'],
                data['type'],
                data['guild'],
                resolve_game_path(data['image_path']),
                orbit_radius,
                angle,
                self.map_center_x,
                self.map_center_y,
                start_pos,
                map_path=self._map_path(data),
            )
            self.planets.append(planet)
            self.orbits.append(orbit_radius)
            last_orbit_radius = orbit_radius

    @staticmethod
    def _map_path(data):
        """The landing map a body names, or None if it has none."""
        return resolve_game_path(data['map']) if data.get('map') else None

    def _mid_system_point(self, size):
        """Top-left of a station image `size` px square, STATION_GAP clear of the sun."""
        half = size / 2
        distance = SUN_RADIUS + STATION_GAP + half
        cx = self.map_center_x + distance * math.cos(STATION_ANGLE)
        cy = self.map_center_y + distance * math.sin(STATION_ANGLE)
        return (int(cx - half), int(cy - half))

    def generate_objects(self, object_data):
        self.objects = []
        for data in object_data:
            image_path = resolve_game_path(data['image_path'])
            if data.get("anchor") == "mid" and self.planets:
                x, y = self._mid_system_point(load_image(image_path).get_width())
            else:
                x, y = data["x"], data["y"]
            obj = SpaceObject(
                body_id(self.id, data['id']),
                data['name'],
                data['type'],
                image_path,
                x,
                y,
                data.get('guild'),
                data.get('access'),
                map_path=self._map_path(data),
            )
            self.objects.append(obj)

    def spawn_point(self):
        """Where a new run starts: in the approach lane under the first station bay."""
        for obj in self.objects:
            for x, y in obj.access_points():
                return (x, y + SPAWN_BELOW_BAY)
        return (self.map_center_x + SUN_RADIUS + STATION_GAP, self.map_center_y)

    def heat_at(self, point):
        """Damage per turn from the sun: none past HEAT_START, rising steeply to HEAT_MAX at the core."""
        depth = math.dist(point, (self.map_center_x, self.map_center_y)) / SUN_RADIUS
        if depth >= HEAT_START:
            return 0.0
        return HEAT_MAX * ((HEAT_START - depth) / HEAT_START) ** 2

    def patrol_zones(self):
        """Centres of the Assembly's patrol zones: its worlds and stations."""
        centres = [planet.position for planet in self.planets if planet.planet_guild == LAW]
        return centres + [obj.world_center() for obj in self.objects if obj.planet_guild == LAW]

    def in_patrol_zone(self, point):
        return any(math.dist(point, centre) <= PATROL_RADIUS for centre in self.patrol_zones())

    def draw(self, screen, camera):
        self.draw_sun(screen, camera)
        self.draw_orbits(screen, camera)
        if self.name_font is None:
            self.name_font = pygame.font.Font(resolve_game_path("space/assets/fonts/OfficeCodePro-Light.ttf"), 14)
        font = self.name_font

        for obj in self.objects:
            obj.draw(screen, camera)

        for planet in self.planets:
            if self.is_orbit_visible(planet.orbit_radius, camera):
                self.draw_planet_name_along_orbit(planet, font, screen, camera, planet.orbit_radius)

            planet.draw(screen, camera)

    def draw_sun(self, screen, camera):
        rect = self.sun_image.get_rect(center=(self.map_center_x, self.map_center_y))
        if camera.colliderect(rect):
            screen.blit(self.sun_image, (rect.x - camera.x, rect.y - camera.y))

    def draw_orbits(self, screen, camera):
        center = (self.map_center_x - camera.x, self.map_center_y - camera.y)
        for radius in self.orbits:
            if self.is_orbit_visible(radius, camera):
                pygame.draw.circle(screen, ORBIT_COLOR, center, radius, 1)

    
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
