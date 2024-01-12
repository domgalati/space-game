# This file handles the main loop when the player is traversing a star system

import pygame
from util.config import SCREEN_WIDTH, SCREEN_HEIGHT, TILE_SIZE
from .input_handler import InputHandler, determine_direction, update_parallax
from .nightsky import initialize_stars, draw_stars, PARALLAX_FACTOR, PARALLAX_DAMPING_FACTOR, VELOCITY_THRESHOLD
from util.sprite_animation import AnimatedSprite
from .star_systems import StarSystem

class StarSystemMode:
    def __init__(self, player):
        self.sol_system = StarSystem('space/star_systems/sol.json')
        self.input_handler = InputHandler(self.sol_system, self)  # Instantiate InputHandler
        self.grid_size = (self.sol_system.MAP_WIDTH // TILE_SIZE, self.sol_system.MAP_HEIGHT // TILE_SIZE)
        self.white_stars, self.purple_stars, self.blue_stars = initialize_stars(SCREEN_WIDTH, SCREEN_HEIGHT)
        self.map_center_x = self.sol_system.MAP_WIDTH // 2
        self.map_center_y = self.sol_system.MAP_HEIGHT // 2
        self.cargo_sheet = 'space/assets/img/cargo6frame.png'
        self.frame_dimensions = (48, 48)
        self.num_frames = 6
        self.animated_cargoship = AnimatedSprite(self.cargo_sheet, self.frame_dimensions, self.num_frames)
        self.current_direction = "southeast"
        self.x_position = self.map_center_x // TILE_SIZE
        self.y_position = self.map_center_y // TILE_SIZE
        self.previous_x, self.previous_y = self.x_position, self.y_position
        self.parallax_offset_x, self.parallax_offset_y = 0, 0
        self.parallax_velocity_x, self.parallax_velocity_y = 0, 0
        self.camera = pygame.Rect(0, 0, SCREEN_WIDTH, SCREEN_HEIGHT)
        self.landing_requested = False
        self.player = player
        self.selected_planet = None

    def handle_input(self):
        # Handle input specific to this mode
        self.x_position, self.y_position = self.input_handler.handle_movement(self.x_position, self.y_position, self.grid_size)
        new_direction = determine_direction(self.x_position, self.y_position, self.previous_x, self.previous_y)
        if new_direction:
            self.current_direction = new_direction

    def check_collision(self):
        ship_rect = pygame.Rect(self.x_position * TILE_SIZE, self.y_position * TILE_SIZE, TILE_SIZE, TILE_SIZE)
        for planet in self.sol_system.planets:
            if ship_rect.colliderect(planet.get_rect()):
                return planet
        for obj in self.sol_system.objects:
            if ship_rect.colliderect(obj.get_rect()):
                return obj
        return None
    
    def show_interaction_menu(self, entity):
        from modes.star_system_mode.menu import InteractionMenu
        # Example options - you can customize these based on the entity
        options = ["Scan", "Hail", "Dock", "Test"]

        # Position the menu in the middle of the screen
        menu_position = (SCREEN_WIDTH // 2 + 50, SCREEN_HEIGHT // 2 + 50)

        # Create and activate the interaction menu
        self.interaction_menu = InteractionMenu(options, menu_position, "space/assets/fonts/OfficeCodePro-Light.ttf")
        self.interaction_menu.activate()

    def get_selected_planet(self):
        return self.selected_planet
    
    def get_player(self):
        # Assuming self.player is an attribute holding the player's state
        return self.player

    def update(self, events):
        self.handle_continuous_updates()
        for event in events:
            if hasattr(self, 'interaction_menu') and self.interaction_menu.active:
                selected_action = self.interaction_menu.update(event)
                if selected_action == "Dock":
                    self.landing_requested = True
                    self.selected_planet = self.check_collision()  # Assuming this returns the planet
            else:
                self.handle_continuous_updates()
                        
    def handle_continuous_updates(self):
        self.handle_input()
    # Update logic for continuous effects like parallax
        self.parallax_offset_x, self.parallax_offset_y, self.parallax_velocity_x, self.parallax_velocity_y = update_parallax(
                        self.x_position, self.y_position, self.previous_x, self.previous_y,
                        self.parallax_offset_x, self.parallax_offset_y, self.parallax_velocity_x, self.parallax_velocity_y,
                        PARALLAX_FACTOR, PARALLAX_DAMPING_FACTOR, VELOCITY_THRESHOLD
                    )
        self.previous_x, self.previous_y = self.x_position, self.y_position
        self.animated_cargoship.update()
        self.camera.x = max(0, min(self.x_position * TILE_SIZE - SCREEN_WIDTH // 2, self.sol_system.MAP_WIDTH - SCREEN_WIDTH))
        self.camera.y = max(0, min(self.y_position * TILE_SIZE - SCREEN_HEIGHT // 2, self.sol_system.MAP_HEIGHT - SCREEN_HEIGHT))
        self.input_handler.handle_interaction(self.x_position, self.y_position, TILE_SIZE)
        # Update the interaction menu if it's active
        if hasattr(self, 'interaction_menu') and self.interaction_menu.active:
            for event in pygame.event.get():
                self.interaction_menu.update(event)

    def draw(self, screen):
        # Draw logic specific to star system mode
        screen.fill((0, 0, 0))
        self.sol_system.draw(screen, self.camera)
        draw_stars(screen, self.white_stars, SCREEN_WIDTH, SCREEN_HEIGHT, (self.parallax_offset_x * 2, self.parallax_offset_y * 2))
        draw_stars(screen, self.purple_stars, SCREEN_WIDTH, SCREEN_HEIGHT, (self.parallax_offset_x * 3, self.parallax_offset_y * 3))
        draw_stars(screen, self.blue_stars, SCREEN_WIDTH, SCREEN_HEIGHT, (self.parallax_offset_x * 4, self.parallax_offset_y * 4))
        spaceship_frame = self.animated_cargoship.get_frame(self.current_direction)
        screen.blit(spaceship_frame, (self.x_position * TILE_SIZE - self.camera.x, self.y_position * TILE_SIZE - self.camera.y))
        
        # Draw collision detection text
        collided_entity = self.check_collision()
        if collided_entity:
            font = pygame.font.Font(None, 36)
            text_surface = font.render("[E] Interact", True, (255, 255, 255))
            screen.blit(text_surface, (SCREEN_WIDTH // 2 - text_surface.get_width() // 2, SCREEN_HEIGHT // 2))
        
        # Draw interaction menu if its active.
        if hasattr(self, 'interaction_menu') and self.interaction_menu.active:
            self.interaction_menu.draw(screen)
        
        print(f"camera: {self.camera}")