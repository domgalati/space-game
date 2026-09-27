import yaml
import pygame
#import pytmx
import random
import time
#from pytmx.util_pygame import load_pygame
from util.config import SCREEN_WIDTH, SCREEN_HEIGHT, TILE_SIZE, resolve_game_path
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
        economy_file_path = resolve_game_path("space/src/util/economy/economy.yaml")
        with open(economy_file_path, "r") as file:
            economy_data = yaml.safe_load(file)

        self.planet = selected_planet
        self.player = Player()
        self.screen = screen
        self.player_sprite = pygame.image.load(
            resolve_game_path("space/assets/img/objects/player.png")
        ).convert_alpha()
        self.ui_planetary = UI_Planetary()  # Create an instance of UI_Planetary       
        self.font = pygame.font.Font(resolve_game_path("space/assets/fonts/Modern Pixel.otf"), 16)
        self.logger = Logger(log_height=200, screen_width=SCREEN_WIDTH, font=self.font)
        self.camera = pygame.Rect(0, 0, SCREEN_WIDTH - self.ui_planetary.sidebar_width, SCREEN_HEIGHT - self.logger.log_height)
        self.map_surface = pygame.Surface((SCREEN_WIDTH - self.ui_planetary.sidebar_width, SCREEN_HEIGHT - self.logger.log_height))
        map_filename = resolve_game_path(f"space/assets/maps/{self.planet.name}.tmx")       
        self.map_manager = MapManager(map_filename, (SCREEN_WIDTH, SCREEN_HEIGHT), (SCREEN_WIDTH, SCREEN_HEIGHT))
        self.log_messages = []
        self.player_position = self._player_start()
        self.map_manager.initialize_animation_data()
        self.economy = Economy(selected_planet.name, economy_data)
        self.economy.set_log_callback(self.logger.add_log_message)
        self.npc_manager = NPCManager(self.map_manager, selected_planet)
        self.interaction_manager = InteractionManager(
            self.map_manager, self.npc_manager, self.logger, economy=self.economy
        )
        self.interaction_manager.set_terminal_callback(self.activate_terminal)
        self.terminal = None
        self.switch_to_star_system_mode = False  # Initialize the attribute here

        self.clock = pygame.time.Clock()
        self.move_repeat_ms = 120  # delay between steps while a direction key is held
        self.next_move_time = 0
        self._blocked_move_logged = False

        self.npc_layer = pygame.surface.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        self.player_layer = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        self.ui_layer = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        self.interaction_layer = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        self.interaction_active = False  # Flag to indicate if an interaction layer is active


    def _player_start(self):
        """Generated maps mark a "Player Start" spawn; hand-made ones use the planet's start_pos."""
        try:
            spawns = self.map_manager.tmx_data.get_layer_by_name("Spawns")
        except ValueError:
            return list(self.planet.start_pos)
        for obj in spawns:
            if obj.name == "Player Start":
                return [int(obj.x), int(obj.y)]
        return list(self.planet.start_pos)

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
        
    def _movement_delta_from_keys(self, keys):
        """Return (dx, dy) in pixels from currently held movement keys (8-directional)."""
        # Numpad diagonals take priority so KP7/9/1/3 stay distinct from arrow chords.
        if keys[pygame.K_KP7]:
            return -TILE_SIZE, -TILE_SIZE
        if keys[pygame.K_KP9]:
            return TILE_SIZE, -TILE_SIZE
        if keys[pygame.K_KP1]:
            return -TILE_SIZE, TILE_SIZE
        if keys[pygame.K_KP3]:
            return TILE_SIZE, TILE_SIZE

        dx = 0
        dy = 0
        if keys[pygame.K_LEFT] or keys[pygame.K_KP4]:
            dx -= TILE_SIZE
        if keys[pygame.K_RIGHT] or keys[pygame.K_KP6]:
            dx += TILE_SIZE
        if keys[pygame.K_UP] or keys[pygame.K_KP8]:
            dy -= TILE_SIZE
        if keys[pygame.K_DOWN] or keys[pygame.K_KP2]:
            dy += TILE_SIZE
        return dx, dy

    def _try_move(self, dx, dy):
        new_position = [self.player_position[0] + dx, self.player_position[1] + dy]
        tile_x, tile_y = new_position[0] // TILE_SIZE, new_position[1] // TILE_SIZE
        if self.is_tile_walkable(tile_y, tile_x):
            self.player_position = new_position
            self._blocked_move_logged = False
            self.update_camera()
            player_tile = (tile_x, tile_y)
            # Advance NPC turns first; adjacent NPCs freeze so E stays valid.
            self.npc_manager.update(
                self.camera.x,
                self.camera.y,
                self.camera.width,
                self.camera.height,
                player_tile=player_tile,
            )
            self.interaction_manager.check_for_adjacent_interactables(
                self.player_position, TILE_SIZE
            )
            self.economy.fire_event()
            self.economy.dump_updated_data("space/src/util/economy/economy_generated.yaml")
            print(f"Player position: {self.player_position}")
            print(f"Camera position: {self.camera}")
            return True

        if not self._blocked_move_logged:
            self.logger.add_log_message("You can't go that way!")
            self._blocked_move_logged = True
        return False

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
            return

        for event in events:
            if event.type == pygame.MOUSEWHEEL:
                self.logger.log_scroll_position -= event.y * 20
                self.logger.log_scroll_position = max(0, min(self.logger.log_scroll_position, self.logger.max_log_scroll))
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_e:
                self.interaction_manager.interact(self.player_position, TILE_SIZE)

        keys = pygame.key.get_pressed()
        dx, dy = self._movement_delta_from_keys(keys)
        if dx == 0 and dy == 0:
            self.next_move_time = 0  # allow an immediate step on the next press
            self._blocked_move_logged = False
            return

        now = pygame.time.get_ticks()
        if now >= self.next_move_time:
            self._try_move(dx, dy)
            self.next_move_time = now + self.move_repeat_ms

    def update(self, events):
        dt = self.clock.tick(60) / 1000.0  # Convert milliseconds to seconds
        if self.terminal and self.terminal.active:
            self.terminal.update(dt)
        self.handle_input(events)
        self.update_camera()
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

    def activate_terminal(self, terminal_type="docking"):
        self.interaction_layer.fill((0, 0, 0, 0))  # Clear the layer
        # Load the docking terminal interface image
        terminal_image = pygame.image.load(
            resolve_game_path("space/assets/img/objects/terminal_screen.png")
        ).convert_alpha() 
        # Resize the image to fit the map_surface
        #terminal_image = pygame.transform.scale(terminal_image, (SCREEN_WIDTH - self.sidebar_width, SCREEN_HEIGHT - self.log_height))   
        # Draw the image onto the map_surface
        self.interaction_layer.blit(terminal_image, (0, 0))
        self.interaction_active = True
        self.terminal = Terminal(terminal_type=terminal_type, planetary_mode=self, planet_name=self.planet)
        self.terminal.activate()
        pass

    def deactivate_terminal(self):
        self.terminal = None
        self.interaction_active = False
        self.draw(self.screen)
        

# Usage example
# planetary_mode = PlanetaryMode(selected_planet, player)
# planetary_mode.land_on_planet()