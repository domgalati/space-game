import pygame
import random
from util.config import TILE_SIZE
from .npc_generator import generate_npc  # Import the npc_generator function

class NPCManager:
    def __init__(self, map_manager, planet):
        self.map_manager = map_manager
        self.planet = planet
        self.npcs = []
        self.populate_npcs()

    def populate_npcs(self):
        npc_types = self.get_npc_types_based_on_planet(self.planet)
        walkable_tiles = self.get_walkable_tiles()
        guild_name = self.planet.planet_guild  # Assuming guild name is stored in planet object

        for npc_class in npc_types:
            num_of_npcs = random.randint(10, 50) # Generates a random number between 1 and 10
            for _ in range(num_of_npcs):
                position = random.choice(walkable_tiles)
                # Use npc_generator to create NPC instance
                npc = generate_npc(guild_name, npc_class)
                npc.position = position
                npc.npc_manager = self # Pass reference of NPC_Manager to npc instance
                if npc.sprite:  # Load the sprite image once during creation of each NPC
                    npc.sprite_image = pygame.image.load(npc.sprite).convert_alpha()
                self.npcs.append(npc)

    def get_npc_types_based_on_planet(self, planet):
        # Example logic based on planet type
        if planet.planet_type == 'Industrial':
            return ["Miner", "Foreman"]  # More miners and foremen for a mining planet
        # Add other conditions for different planet types
        return [NPC]  # Default NPC type

    def get_walkable_tiles(self):
        walkable_tiles = []
        walkable_layer = self.map_manager.tmx_data.get_layer_by_name('walkable')
        for x, y, gid in walkable_layer:
            if gid != 0:  # Assuming non-zero GID indicates a walkable tile
                walkable_tiles.append((x, y))
        return walkable_tiles

    def is_within_visible_area(self, npc_x, npc_y, camera_x, camera_y, camera_width, camera_height):
            # Convert NPC position from tiles to pixels if necessary
            npc_pixel_x = npc_x * TILE_SIZE
            npc_pixel_y = npc_y * TILE_SIZE
    
            # Check if the NPC's position intersects with the camera's viewport
            return (camera_x <= npc_pixel_x <= camera_x + camera_width and
                    camera_y <= npc_pixel_y <= camera_y + camera_height)

    def update(self, camera_x, camera_y, camera_width, camera_height):
        for npc in self.npcs:
            if self.is_within_visible_area(npc.position[0], npc.position[1], camera_x, camera_y, camera_width, camera_height):
                npc.update()

    def draw(self, npc_layer, camera):
        npc_layer.fill((0, 0, 0, 0)) 
        for npc in self.npcs:
            if self.is_within_visible_area(npc.position[0], npc.position[1], camera.x, camera.y, camera.width, camera.height):
                if npc.sprite:
                    sprite_image = npc.sprite_image
                    npc_screen_x = npc.position[0] * TILE_SIZE - camera.x
                    npc_screen_y = npc.position[1] * TILE_SIZE - camera.y
                    npc_layer.blit(sprite_image, (npc_screen_x, npc_screen_y))