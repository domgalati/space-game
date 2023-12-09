import pygame
from pygame.locals import Rect
import os
from nightsky import generate_stars, draw_stars
from sprite_animation import AnimatedSprite
from config import SCREEN_WIDTH, SCREEN_HEIGHT
from input_handler import handle_movement, determine_direction, update_parallax

# Initialize Pygame
pygame.init()

# Constants
TILE_SIZE = 24
MAP_WIDTH, MAP_HEIGHT = SCREEN_WIDTH * 8, SCREEN_HEIGHT * 8 # Map Size Constants

# Set up display
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("working title")
grid_size = (SCREEN_WIDTH // TILE_SIZE, SCREEN_HEIGHT // TILE_SIZE)
clock = pygame.time.Clock()

##################
## Star properties
parallax_factor = 0.5  # Adjust this for the effect strength
parallax_offset_x, parallax_offset_y = 0, 0 # Initialize parallax offset variables
parallax_velocity_x, parallax_velocity_y = 0, 0
parallax_damping_factor = 0.95  # Adjust this value to control the inertia effect
velocity_threshold = 0.1  # Adjust this value based on testing
star_size_options = [.5, 1, 2]  # Different sizes for variety
white_stars = generate_stars(100, SCREEN_WIDTH, SCREEN_HEIGHT, star_size_options, (255, 255, 255))
purple_stars = generate_stars(50, SCREEN_WIDTH, SCREEN_HEIGHT, star_size_options, (51, 0, 51))
blue_stars = generate_stars(75, SCREEN_WIDTH, SCREEN_HEIGHT, star_size_options, (185, 217, 235)) 

# ####################
# Planet Properties
PLANET_SIZE = 64  # Size of the planet images
planet_image = pygame.image.load('space/img/planet.png')
planets = [
    # Example planet positions
    (500, 300), 
    (1500, 800),
    # Add more planets as needed
]
#
# Function to draw planets
def draw_planets(surface, planets, planet_image):
    for planet_pos in planets:
        surface.blit(planet_image, planet_pos)

## ####################
# Map Properties
# Create a surface for the map
map_surface = pygame.Surface((MAP_WIDTH, MAP_HEIGHT))
# map_surface.fill((0, 0, 0))  # Fill with black, representing space

# Drawing the planets on the map surface
draw_planets(map_surface, planets, planet_image)


# #####################
# Cargo Ship properties
cargo_sheet = 'space/img/cargo6frame.png'
frame_dimensions = (48, 48)  # Width and height of each frame
num_frames = 6  # Total number of frames in the sprite sheet
animated_cargoship = AnimatedSprite(cargo_sheet, frame_dimensions, num_frames)
current_direction = "south"

# ######################
# Main loop
running = True
x_position, y_position = 24, 24
previous_x, previous_y = x_position, y_position # Initializing positions for paralax
camera = Rect(0, 0, SCREEN_WIDTH, SCREEN_HEIGHT)  # Initial camera position

while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.KEYDOWN:
            # Movement on keypress
            x_position, y_position = handle_movement(event, x_position, y_position, grid_size)

    new_direction = determine_direction(x_position, y_position, previous_x, previous_y)
    if new_direction is not None:
        current_direction = new_direction

    # Calculate parallax offset
    parallax_offset_x, parallax_offset_y, parallax_velocity_x, parallax_velocity_y = update_parallax(
        x_position, y_position, previous_x, previous_y, 
        parallax_offset_x, parallax_offset_y, 
        parallax_velocity_x, parallax_velocity_y, 
        parallax_factor, parallax_damping_factor, 
        velocity_threshold
    )

    # Update the previous position for the next iteration
    previous_x, previous_y = x_position, y_position

    # Update camera position based on spaceship position
    camera.center = (x_position * TILE_SIZE, y_position * TILE_SIZE)

    # Keep the camera within bounds of the map
    camera.clamp_ip(Rect(0, 0, MAP_WIDTH, MAP_HEIGHT))
    
    # Framerate
    clock.tick(24)
    # Drawing the game
    screen.fill((0, 0, 0))  # Black background
    screen.blit(map_surface, (0, 0), camera)  # Draw the portion of the map within the camera view
    draw_stars(screen, white_stars, SCREEN_WIDTH, SCREEN_HEIGHT, (parallax_offset_x * 2, parallax_offset_y * 2))
    draw_stars(screen, purple_stars, SCREEN_WIDTH, SCREEN_HEIGHT, (parallax_offset_x * 3, parallax_offset_y * 3))
    draw_stars(screen, blue_stars, SCREEN_WIDTH, SCREEN_HEIGHT, (parallax_offset_x * 4, parallax_offset_y * 4))

    animated_cargoship.update()
    spaceship_frame = animated_cargoship.get_frame(current_direction)
    screen.blit(spaceship_frame, (x_position * TILE_SIZE, y_position * TILE_SIZE))
    
    pygame.display.flip()  # Update the display
    
pygame.quit()

