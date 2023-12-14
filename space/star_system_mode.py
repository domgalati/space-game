# This file handles the main loop when the player is traversing a star system

import pygame
from config import SCREEN_WIDTH, SCREEN_HEIGHT, TILE_SIZE
from input_handler import InputHandler, determine_direction, update_parallax
from nightsky import initialize_stars, draw_stars, PARALLAX_FACTOR, PARALLAX_DAMPING_FACTOR, VELOCITY_THRESHOLD
from sprite_animation import AnimatedSprite
from star_systems import StarSystem

class StarSystemMode:
    def __init__(self):
        self.input_handler = InputHandler()  # Instantiate InputHandler
        self.sol_system = StarSystem('space/star_systems/sol.json')
        self.grid_size = (self.sol_system.MAP_WIDTH // TILE_SIZE, self.sol_system.MAP_HEIGHT // TILE_SIZE)
        self.white_stars, self.purple_stars, self.blue_stars = initialize_stars(SCREEN_WIDTH, SCREEN_HEIGHT)
        self.map_center_x = self.sol_system.MAP_WIDTH // 2
        self.map_center_y = self.sol_system.MAP_HEIGHT // 2
        self.cargo_sheet = 'space/img/cargo6frame.png'
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

    def handle_input(self):
        # Handle input specific to this mode
        self.x_position, self.y_position = self.input_handler.handle_movement(self.x_position, self.y_position, self.grid_size)
        new_direction = determine_direction(self.x_position, self.y_position, self.previous_x, self.previous_y)
        if new_direction:
            self.current_direction = new_direction
            
    def update(self):
        # Update logic specific to star system mode
        self.handle_input()
        self.parallax_offset_x, self.parallax_offset_y, self.parallax_velocity_x, self.parallax_velocity_y = update_parallax(
            self.x_position, self.y_position, self.previous_x, self.previous_y,
            self.parallax_offset_x, self.parallax_offset_y, self.parallax_velocity_x, self.parallax_velocity_y,
            PARALLAX_FACTOR, PARALLAX_DAMPING_FACTOR, VELOCITY_THRESHOLD
        )
        self.previous_x, self.previous_y = self.x_position, self.y_position
        self.animated_cargoship.update()
        self.camera.x = max(0, min(self.x_position * TILE_SIZE - SCREEN_WIDTH // 2, self.sol_system.MAP_WIDTH - SCREEN_WIDTH))
        self.camera.y = max(0, min(self.y_position * TILE_SIZE - SCREEN_HEIGHT // 2, self.sol_system.MAP_HEIGHT - SCREEN_HEIGHT))

    def draw(self, screen):
        # Draw logic specific to star system mode
        screen.fill((0, 0, 0))
        self.sol_system.draw(screen, self.camera)
        draw_stars(screen, self.white_stars, SCREEN_WIDTH, SCREEN_HEIGHT, (self.parallax_offset_x * 2, self.parallax_offset_y * 2))
        draw_stars(screen, self.purple_stars, SCREEN_WIDTH, SCREEN_HEIGHT, (self.parallax_offset_x * 3, self.parallax_offset_y * 3))
        draw_stars(screen, self.blue_stars, SCREEN_WIDTH, SCREEN_HEIGHT, (self.parallax_offset_x * 4, self.parallax_offset_y * 4))
        spaceship_frame = self.animated_cargoship.get_frame(self.current_direction)
        screen.blit(spaceship_frame, (self.x_position * TILE_SIZE - self.camera.x, self.y_position * TILE_SIZE - self.camera.y))
