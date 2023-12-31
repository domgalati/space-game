import pygame
import pytmx
from pytmx.util_pygame import load_pygame
from util.config import SCREEN_WIDTH, SCREEN_HEIGHT, TILE_SIZE

class MapManager:
    def __init__(self, map_filename, tileset, screen_dimensions, camera_dimensions):
        # Initialize attributes
        self.tmx_data = self.load_map(map_filename)
        self.map_surface = pygame.Surface(screen_dimensions)
        self.sidebar_width = 200
        self.log_height = 200
        self.tileset = tileset
        self.animations = {}
        # Other necessary initializations

    def initialize_map_tiles(self):
        # Load tiles from the tileset and store them in a dictionary
        tiles = {}
        # Add logic here to load individual tiles from the tileset based on the planet type
        return tiles

    def load_map(self, map_filename):
        tmx_data = load_pygame(map_filename)
        return tmx_data

    def draw_map(self, surface, camera):
        surface.fill((0, 0, 0))
        for layer in self.tmx_data.visible_layers:
            if isinstance(layer, pytmx.TiledTileLayer):
                for x, y, gid in layer:
                    animation = self.animations.get(gid)
                    if animation:
                        tile_gid = animation['frames'][animation['current_frame']]
                        tile = self.tmx_data.get_tile_image_by_gid(tile_gid)
                    else:
                        tile = self.tmx_data.get_tile_image_by_gid(gid)

                    if tile:
                        surface.blit(tile, (x * self.tmx_data.tilewidth - camera.x, y * self.tmx_data.tileheight - camera.y))
    
    def update_animations(self, dt):
        for animation in self.animations.values():
            animation['timer'] += dt
            if animation['timer'] > animation['durations'][animation['current_frame']]:
                animation['timer'] -= animation['durations'][animation['current_frame']]
                animation['current_frame'] = (animation['current_frame'] + 1) % len(animation['frames'])
