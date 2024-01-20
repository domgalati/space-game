import yaml
import pygame
#import pytmx
import random
import time
#from pytmx.util_pygame import load_pygame
from util.config import SCREEN_WIDTH, SCREEN_HEIGHT, TILE_SIZE
from .logger import Logger
from .map_manager import MapManager
from .ui_planetary import UI_Planetary
from .interaction_manager import InteractionManager
from .terminal import Terminal
from util.economy.economy import Economy
from entities.player import Player
from .npc_manager import NPCManager

class PlanetaryMode:
    def __init__(self, selected_planet, player, screen): 
        economy_file_path = 'space/src/util/economy/economy.yaml'
        with open(economy_file_path, 'r') as file:
            economy_data = yaml.safe_load(file)

        self.planet = selected_planet
        self.player = Player()
        self.screen = screen
        self.player_sprite = pygame.image.load("space/assets/img/objects/player.png").convert_alpha()
        self.ui_planetary = UI_Planetary()  # Create an instance of UI_Planetary       
        self.font = pygame.font.Font("space/assets/fonts/Modern Pixel.otf", 16)
        self.logger = Logger(log_height=200, screen_width=SCREEN_WIDTH, font=self.font)
        self.camera = pygame.Rect(0, 0, SCREEN_WIDTH - self.ui_planetary.sidebar_width, SCREEN_HEIGHT - self.logger.log_height)
        self.map_surface = pygame.Surface((SCREEN_WIDTH - self.ui_planetary.sidebar_width, SCREEN_HEIGHT - self.logger.log_height))
        map_filename = f"space/assets/maps/{self.planet.name}.tmx"       
        self.map_manager = MapManager(map_filename, (SCREEN_WIDTH, SCREEN_HEIGHT), (SCREEN_WIDTH, SCREEN_HEIGHT))
        self.log_messages = []
        self.player_position = list(self.planet.start_pos)
        self.map_manager.initialize_animation_data()
        self.npc_manager = NPCManager(self.map_manager, selected_planet)
        self.interaction_manager = InteractionManager(self.map_manager, self.npc_manager, self.logger)
        self.interaction_manager.set_terminal_callback(self.activate_terminal)
        self.terminal = None
        self.switch_to_star_system_mode = False  # Initialize the attribute here
        self.economy = Economy(selected_planet.name, economy_data)
        self.economy.set_log_callback(self.logger.add_log_message)



        self.clock = pygame.time.Clock()

        self.npc_layer = pygame.surface.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        self.player_layer = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        self.ui_layer = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        self.interaction_layer = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        self.interaction_active = False  # Flag to indicate if an interaction layer is active


    def is_tile_walkable(self, x, y):
        # Access the 'walkable' layer
        walkable_layer = self.map_manager.tmx_data.get_layer_by_name("walkable")
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
        #self.map_manager.camera.clamp_ip(pygame.Rect(0, 0, self.tmx_data.width * TILE_SIZE, self.tmx_data.height * TILE_SIZE))
        
    def handle_input(self, events):
        if self.terminal and self.terminal.active:
            for event in events:
                if event.type == pygame.KEYDOWN:
                    self.terminal.process_input(event)
                elif event.type == pygame.MOUSEWHEEL:
                    if event.y > 0:
                        self.terminal.scroll_up()
                    elif event.y < 0:
                        self.terminal.scroll_down()
        else:
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
                        self.interaction_manager.interact(self.player_position, TILE_SIZE)

                    if new_position != self.player_position:
                        tile_x, tile_y = new_position[0] // TILE_SIZE, new_position[1] // TILE_SIZE
                        if self.is_tile_walkable(tile_y, tile_x):
                            self.player_position = new_position
                            moved = True
                        else:
                            self.logger.add_log_message(f"You can't go that way!")

                    if moved:
                        self.update_camera()
                        self.interaction_manager.check_for_adjacent_interactables(self.player_position, TILE_SIZE)
                        self.economy.fire_event()
                        self.economy.dump_updated_data('space/src/util/economy/economy_generated.yaml')
                        self.npc_manager.update(self.camera.x, self.camera.y, self.camera.width, self.camera.height)
                        print(f"Player position: {self.player_position}")
                        print(f"Camera position: {self.camera}")

    def update(self, events):
        dt = self.clock.tick(60) / 1000.0  # Convert milliseconds to seconds
        if self.terminal and self.terminal.active:
            self.terminal.update(dt)
        self.handle_input(events)
        self.update_camera()
        # self.npc_manager.update()
        self.ui_planetary.update_player_stats(self.player)
        # Add additional update logic if necessary

    def draw_player(self):
        self.player_layer.fill((0, 0, 0, 0))  # Clear the layer
        self.player_layer.fill((0, 0, 0, 0))  # Clear the layer (with transparency)
        player_x = self.player_position[0] - self.camera.x
        player_y = self.player_position[1] - self.camera.y
        self.player_layer.blit(self.player_sprite, (player_x, player_y))

    def draw_ui(self):
        self.ui_layer.fill((0, 0, 0, 0))

    def draw(self, screen):
        screen.fill((0, 0, 0))
        self.map_manager.draw_map(self.map_surface, self.camera)

        # self.draw_player()
        # self.map_surface.blit(self.player_layer, (0, 0))

        self.draw_ui()
        self.map_surface.blit(self.ui_layer, (0, 0))

        self.npc_manager.draw(self.npc_layer, self.camera)
        self.map_surface.blit(self.npc_layer, (0, 0))  # Draw the NPC layer onto the map surface

        self.draw_player()
        self.map_surface.blit(self.player_layer, (0, 0))

        if self.interaction_active:
            self.map_surface.blit(self.interaction_layer, (0, 0))
        
        screen.blit(self.map_surface, (0, 0))

        self.ui_planetary.draw_sidebar()
        self.logger.draw_log()
        screen.blit(self.map_surface, (0, 0))
        screen.blit(self.ui_planetary.sidebar_surface, (SCREEN_WIDTH - self.ui_planetary.sidebar_width, 0))
        screen.blit(self.logger.log_surface, (0, SCREEN_HEIGHT - self.logger.log_height))
        
        if self.terminal and self.terminal.active:
            self.terminal.display(screen)

    def land_on_planet(self):
        # Logic to initialize the planetary landing, setting the initial position of the player, etc.
        self.logger.add_log_message(f"You have landed on {self.planet.name}")
        pass

    def return_to_star_system_mode(self):
        # Any necessary cleanup or state saving goes here
        # ...

        # Signal to switch back to StarSystemMode
        self.switch_to_star_system_mode = True

    def activate_terminal(self):
        self.interaction_layer.fill((0, 0, 0, 0))  # Clear the layer
        # Load the docking terminal interface image
        terminal_image = pygame.image.load("space/assets/img/objects/terminal_screen.png").convert_alpha() 
        # Resize the image to fit the map_surface
        #terminal_image = pygame.transform.scale(terminal_image, (SCREEN_WIDTH - self.sidebar_width, SCREEN_HEIGHT - self.log_height))   
        # Draw the image onto the map_surface
        self.interaction_layer.blit(terminal_image, (0, 0))
        self.interaction_active = True
        self.terminal = Terminal(terminal_type="docking", planetary_mode=self, planet_name=self.planet)
        self.terminal.activate()
        pass

    def deactivate_terminal(self):
        self.terminal = None
        self.interaction_active = False
        self.draw(self.screen)
        

# Usage example
# planetary_mode = PlanetaryMode(selected_planet, player)
# planetary_mode.land_on_planet()