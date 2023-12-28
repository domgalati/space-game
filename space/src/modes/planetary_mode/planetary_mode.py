import pygame
import pytmx
from pytmx.util_pygame import load_pygame
from util.config import SCREEN_WIDTH, SCREEN_HEIGHT, TILE_SIZE

class PlanetaryMode:
    def __init__(self, selected_planet, player): 
        self.planet = selected_planet
        self.player = player
        self.player_sprite = pygame.image.load("space/assets/img/objects/player.png").convert_alpha()
        self.tileset = pygame.image.load("space/assets/img/tilesets/planets.png")
        self.sidebar_width = 200
        self.log_height = 200
        self.map_surface = pygame.Surface((SCREEN_WIDTH - self.sidebar_width, SCREEN_HEIGHT - self.log_height))
        self.sidebar_surface = pygame.Surface((self.sidebar_width, SCREEN_HEIGHT))
        self.log_surface = pygame.Surface((SCREEN_WIDTH, self.log_height))
        self.map_tiles = self.initialize_map_tiles()
        self.log_messages = []
        planet_map_filename = f"space/assets/maps/{self.planet.name}.tmx"
        self.player_position = list(self.planet.start_pos)
        self.tmx_data = self.load_map(planet_map_filename)
        self.camera = pygame.Rect(0, 0, SCREEN_WIDTH - self.sidebar_width, SCREEN_HEIGHT - self.log_height)

    def initialize_map_tiles(self):
        # Load tiles from the tileset and store them in a dictionary
        tiles = {}
        # Add logic here to load individual tiles from the tileset based on the planet type
        return tiles

    def draw_sidebar(self):
        # Draw player stats and other relevant information
        # Add logic to display player stats
        pass

    def draw_log(self):
        # Draw log messages
        for i, message in enumerate(self.log_messages[-5:]):
            text_surface = pygame.font.Font(None, 24).render(message, True, (255, 255, 255))
            self.log_surface.blit(text_surface, (10, i * 20))

    def load_map(self, map_filename):
        tmx_data = load_pygame(map_filename)
        return tmx_data

    def draw_map(self, surface):
        for layer in self.tmx_data.visible_layers:
            if isinstance(layer, pytmx.TiledTileLayer):
                for x, y, gid in layer:
                    tile = self.tmx_data.get_tile_image_by_gid(gid)
                    if tile:
                        surface.blit(tile, (x * self.tmx_data.tilewidth - self.camera.x, y * self.tmx_data.tileheight - self.camera.y))
    
    def update_camera(self):
    # Shift the camera if the player passes the edge of the current screen area
        if self.player_position[0] < self.camera.left:
            self.camera.move_ip(-self.camera.width, 0)
        elif self.player_position[0] >= self.camera.right:
            self.camera.move_ip(self.camera.width, 0)
        if self.player_position[1] < self.camera.top:
            self.camera.move_ip(0, -self.camera.height)
        elif self.player_position[1] >= self.camera.bottom:
            self.camera.move_ip(0, self.camera.height)
        # Constrain the camera to the map bounds
        #self.camera.clamp_ip(pygame.Rect(0, 0, self.tmx_data.width * TILE_SIZE, self.tmx_data.height * TILE_SIZE))
        
    def handle_input(self, events):
        for event in events:
            if event.type == pygame.KEYDOWN:
                moved = False
                if event.key == pygame.K_KP4:
                    self.player_position[0] -= TILE_SIZE
                    moved = True
                elif event.key == pygame.K_KP6:
                    self.player_position[0] += TILE_SIZE
                    moved = True
                elif event.key == pygame.K_KP8:
                    self.player_position[1] -= TILE_SIZE
                    moved = True
                elif event.key == pygame.K_KP2:
                    self.player_position[1] += TILE_SIZE
                    moved = True
                elif event.key == pygame.K_KP7:
                    self.player_position[0] -= TILE_SIZE
                    self.player_position[1] -= TILE_SIZE
                    moved = True
                elif event.key == pygame.K_KP9:
                    self.player_position[0] += TILE_SIZE
                    self.player_position[1] -= TILE_SIZE
                    moved = True
                elif event.key == pygame.K_KP1:
                    self.player_position[0] -= TILE_SIZE
                    self.player_position[1] += TILE_SIZE
                    moved = True
                elif event.key == pygame.K_KP3:
                    self.player_position[0] += TILE_SIZE
                    self.player_position[1] += TILE_SIZE
                    moved = True
                if moved:
                    self.update_camera()
                    print("is looping?")
                    print(f"Player position: {self.player_position}")
                    print(f"Camera position: {self.camera}")

    def update(self, events):
        self.handle_input(events)
        self.update_camera()
        # Add additional update logic if necessary

    def draw_player(self, surface):
        surface.blit(self.player_sprite, (self.player_position[0] - self.camera.x, self.player_position[1] - self.camera.y))

    def draw(self, screen):
        screen.fill((0, 0, 0))
        self.draw_map(self.map_surface)
        self.draw_player(self.map_surface)
        self.draw_sidebar()
        self.draw_log()
        screen.blit(self.map_surface, (0, 0))
        screen.blit(self.sidebar_surface, (SCREEN_WIDTH - self.sidebar_width, 0))
        screen.blit(self.log_surface, (0, SCREEN_HEIGHT - self.log_height))

    def add_log_message(self, message):
        self.log_messages.append(message)

    def land_on_planet(self):
        # Logic to initialize the planetary landing, setting the initial position of the player, etc.
        pass

# Usage example
# planetary_mode = PlanetaryMode(selected_planet, player)
# planetary_mode.land_on_planet()
