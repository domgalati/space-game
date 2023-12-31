import pygame
import pytmx
import random
from pytmx.util_pygame import load_pygame
from util.config import SCREEN_WIDTH, SCREEN_HEIGHT, TILE_SIZE
from .logger import Logger

class PlanetaryMode:
    def __init__(self, selected_planet, player): 
        self.planet = selected_planet
        self.player = player
        self.player_sprite = pygame.image.load("space/assets/img/objects/player.png").convert_alpha()
        self.tileset = pygame.image.load("space/assets/img/tilesets/planets.png")
        self.sidebar_width = 200
        self.font = pygame.font.Font("space/assets/fonts/Modern Pixel.otf", 16)
        self.logger = Logger(log_height=200, screen_width=SCREEN_WIDTH, font=self.font)
        self.map_surface = pygame.Surface((SCREEN_WIDTH - self.sidebar_width, SCREEN_HEIGHT - self.logger.log_height))
        self.sidebar_surface = pygame.Surface((self.sidebar_width, SCREEN_HEIGHT - 200))
        self.map_tiles = self.initialize_map_tiles()
        self.log_messages = []
        planet_map_filename = f"space/assets/maps/{self.planet.name}.tmx"
        self.player_position = list(self.planet.start_pos)
        self.tmx_data = self.load_map(planet_map_filename)
        self.camera = pygame.Rect(0, 0, SCREEN_WIDTH - self.sidebar_width, SCREEN_HEIGHT - self.logger.log_height)
        self.animations = {}
        self.initialize_animation_data()
        
    def initialize_map_tiles(self):
        # Load tiles from the tileset and store them in a dictionary
        tiles = {}
        # Add logic here to load individual tiles from the tileset based on the planet type
        return tiles

    def draw_sidebar(self):
        # Draw player stats and other relevant information
        # Add logic to display player stats
        pass

    def load_map(self, map_filename):
        tmx_data = load_pygame(map_filename)
        return tmx_data

    def initialize_animation_data(self):
        self.animations = {}  # Dictionary to store animation data keyed by tile GID
        for gid, properties in self.tmx_data.tile_properties.items():
            animation = properties.get('frames', None)
            self.animations[gid] = {
                'frames': [frame.gid for frame in animation],
                'durations': [frame.duration for frame in animation],
                'current_frame': 0,
                'timer': 0
            }

    def update_animations(self, dt):
        for animation in self.animations.values():
            animation['timer'] += dt
            if animation['timer'] > animation['durations'][animation['current_frame']]:
                animation['timer'] -= animation['durations'][animation['current_frame']]
                animation['current_frame'] = (animation['current_frame'] + 1) % len(animation['frames'])

    def draw_map(self, surface):
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
                        surface.blit(tile, (x * self.tmx_data.tilewidth - self.camera.x, y * self.tmx_data.tileheight - self.camera.y))
    
    def is_tile_walkable(self, x, y):
        # Access the 'walkable' layer
        walkable_layer = self.tmx_data.get_layer_by_name("walkable")
        if walkable_layer:
            # The layer is structured as a 2D grid. Check if the tile at (x, y) is walkable
            tile = walkable_layer.data[x][y]
            if tile != 0:
                return True
            else:
            # If there is no 'walkable' layer, default to non-walkable
                return False
    
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
            if event.type == pygame.MOUSEWHEEL:
                # Adjust the log scroll position
                self.logger.log_scroll_position -= event.y * 20  # Adjust the multiplier as needed
                self.logger.log_scroll_position = max(0, min(self.logger.log_scroll_position, self.logger.max_log_scroll))

            if event.type == pygame.KEYDOWN:
                new_position = self.player_position.copy()
                moved = False

                if event.key == pygame.K_KP4 or event.key == pygame.K_LEFT:
                    new_position[0] -= TILE_SIZE
                elif event.key == pygame.K_KP6 or event.key == pygame.K_RIGHT:
                    new_position[0] += TILE_SIZE
                elif event.key == pygame.K_KP8 or event.key == pygame.K_UP:
                    new_position[1] -= TILE_SIZE
                elif event.key == pygame.K_KP2 or event.key == pygame.K_DOWN:
                    new_position[1] += TILE_SIZE
                elif event.key == pygame.K_KP7:
                    new_position[0] -= TILE_SIZE
                    new_position[1] -= TILE_SIZE
                elif event.key == pygame.K_KP9:
                    new_position[0] += TILE_SIZE
                    new_position[1] -= TILE_SIZE
                elif event.key == pygame.K_KP1:
                    new_position[0] -= TILE_SIZE
                    new_position[1] += TILE_SIZE
                elif event.key == pygame.K_KP3:
                    new_position[0] += TILE_SIZE
                    new_position[1] += TILE_SIZE
                elif event.key == pygame.K_e:
                    self.interact()

                if new_position != self.player_position:
                    tile_x, tile_y = new_position[0] // TILE_SIZE, new_position[1] // TILE_SIZE
                    if self.is_tile_walkable(tile_y, tile_x):
                        self.player_position = new_position
                        moved = True
                    else:
                        self.logger.add_log_message(f"Your helmet bounces off the hard surface!{random.randint(5,200)}")

                if moved:
                    self.update_camera()
                    self.check_for_adjacent_interactables()
                    print(f"Player position: {self.player_position}")
                    print(f"Camera position: {self.camera}")

    def check_for_adjacent_interactables(self):
        #Check adjacent tiles for interactable items and log a message if found.
        adjacent_positions = [
            (self.player_position[0], self.player_position[1] - TILE_SIZE),  # Up
            (self.player_position[0], self.player_position[1] + TILE_SIZE),  # Down
            (self.player_position[0] - TILE_SIZE, self.player_position[1]),  # Left
            (self.player_position[0] + TILE_SIZE, self.player_position[1])   # Right
        ]

        for pos in adjacent_positions:
            is_interactable, objectname = self.is_interactable_at(pos)
            if is_interactable:
                self.logger.add_log_message(f"You approach a {objectname}. Press E to interact. Testing message display length. This message is really long.")
                break  # Add this if you only want one message per move
            
    def is_interactable_at(self, position):
        """
        Check if the tile at the given position is in the 'interactable' layer.
        add interactable objects layer in the map file, the layer must always be called "Objects".
        Then place tiles where you want the objects to live. Change the "Name" parameter of the object in tiled.
        """
        y, x = position
        tile_x, tile_y = x // TILE_SIZE, y // TILE_SIZE
        if 0 <= tile_x and 0 <= tile_y:
            objects_layer = self.tmx_data.get_layer_by_name('Objects')
            for i in range(len(objects_layer)):
                if objects_layer[i].x == y and objects_layer[i].y == x:
                    objectname = objects_layer[i].name
                    return True, objectname
        return False, None

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
        self.logger.draw_log()
        screen.blit(self.map_surface, (0, 0))
        screen.blit(self.sidebar_surface, (SCREEN_WIDTH - self.sidebar_width, 0))
        screen.blit(self.logger.log_surface, (0, SCREEN_HEIGHT - self.logger.log_height))

    def land_on_planet(self):
        # Logic to initialize the planetary landing, setting the initial position of the player, etc.
        self.logger.add_log_message(f"You have landed on {self.planet.name}")
        pass

    def interact(self):
        #Perform an interaction with an adjacent interactable object.
        ## Copies code from check_for_adjacent_interactables, needs to be optimized.
        adjacent_positions = [
                    (self.player_position[0], self.player_position[1] - TILE_SIZE),  # Up
                    (self.player_position[0], self.player_position[1] + TILE_SIZE),  # Down
                    (self.player_position[0] - TILE_SIZE, self.player_position[1]),  # Left
                    (self.player_position[0] + TILE_SIZE, self.player_position[1])   # Right
                ]
        for pos in adjacent_positions:
            is_interactable, objectname = self.is_interactable_at(pos)
            if is_interactable:
                self.handle_interaction_with(objectname)

    def handle_interaction_with(self, objectname):
        """
        Handle specific interactions based on the object name.
        """
        if objectname == "Docking Terminal":
            self.docking_terminal()
            pass
        # Add more conditions for different objects

    def docking_terminal(self):
        # Load the docking terminal interface image
        terminal_image = pygame.image.load("space/assets/img/objects/terminal_screen.png").convert_alpha() 
        # Resize the image to fit the map_surface
        #terminal_image = pygame.transform.scale(terminal_image, (SCREEN_WIDTH - self.sidebar_width, SCREEN_HEIGHT - self.log_height))   
        # Draw the image onto the map_surface
        self.map_surface.blit(terminal_image, (0, 0))   
        # Call method to handle player input and feedback (to be implemented)
        #self.handle_terminal_input()        
        pass

# Usage example
# planetary_mode = PlanetaryMode(selected_planet, player)
# planetary_mode.land_on_planet()