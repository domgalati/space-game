import os, sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import pygame
import math
from planet import Planet, generate_planets
from pygame.locals import Rect
from nightsky import initialize_stars, draw_stars, PARALLAX_FACTOR, PARALLAX_DAMPING_FACTOR, VELOCITY_THRESHOLD
from sprite_animation import AnimatedSprite
from config import SCREEN_WIDTH, SCREEN_HEIGHT
from input_handler import handle_movement, determine_direction, update_parallax

# Initialize Pygame
pygame.init()
pygame.key.set_repeat(50, 200)  # 1 millisecond delay, 10 milliseconds interval

# Constants
TILE_SIZE = 24
MAP_WIDTH, MAP_HEIGHT = SCREEN_WIDTH * 24, SCREEN_HEIGHT * 24 # Map Size Constants

# Calculate center of the map
map_center_x = MAP_WIDTH // 2
map_center_y = MAP_HEIGHT // 2

# Set up display
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("working title")
grid_size = (MAP_WIDTH // TILE_SIZE, MAP_HEIGHT // TILE_SIZE)
clock = pygame.time.Clock()

##################
## Star properties
parallax_offset_x, parallax_offset_y = 0, 0 # Initialize parallax offset variables
parallax_velocity_x, parallax_velocity_y = 0, 0
white_stars, purple_stars, blue_stars = initialize_stars(SCREEN_WIDTH, SCREEN_HEIGHT)


# ####################
# Planet Properties
map_surface = pygame.Surface((MAP_WIDTH, MAP_HEIGHT)) # Create a surface for the map
json_path ='space/star_systems/sol.json'
planets, orbits = generate_planets(json_path, map_center_x, map_center_y)

# #####################
# Cargo Ship properties
cargo_sheet = 'space/img/cargo6frame.png'
frame_dimensions = (48, 48)  # Width and height of each frame
num_frames = 6  # Total number of frames in the sprite sheet
animated_cargoship = AnimatedSprite(cargo_sheet, frame_dimensions, num_frames)
current_direction = "southeast"

# ######################
# Main loop
running = True

# Initialize ship position at the center of the map
x_position = map_center_x // TILE_SIZE
y_position = map_center_y // TILE_SIZE

previous_x, previous_y = x_position, y_position # Initializing positions for paralax
camera = Rect(0, 0, SCREEN_WIDTH, SCREEN_HEIGHT)  # Initial camera position
camera_bounds = Rect(0, 0, MAP_WIDTH, MAP_HEIGHT) # Calculate camera boundaries


while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.KEYDOWN:
            # Movement on keypress
            x_position, y_position = handle_movement(x_position, y_position, grid_size)

    # Tells ship which way to face
    new_direction = determine_direction(x_position, y_position, previous_x, previous_y)
    if new_direction is not None:
        current_direction = new_direction

    # Calculate parallax offset
    parallax_offset_x, parallax_offset_y, parallax_velocity_x, parallax_velocity_y = update_parallax(
        x_position, y_position, previous_x, previous_y, 
        parallax_offset_x, parallax_offset_y, 
        parallax_velocity_x, parallax_velocity_y, PARALLAX_FACTOR, PARALLAX_DAMPING_FACTOR, VELOCITY_THRESHOLD
    )

    # Update the previous position for the next iteration
    previous_x, previous_y = x_position, y_position

    # Calculate camera position to center on the ship, with boundaries
    camera_center_x = x_position * TILE_SIZE + TILE_SIZE // 2
    camera_center_y = y_position * TILE_SIZE + TILE_SIZE // 2

    # Update camera position based on spaceship position
    camera.x = max(0, min(camera_center_x - SCREEN_WIDTH // 2, MAP_WIDTH - SCREEN_WIDTH))
    camera.y = max(0, min(camera_center_y - SCREEN_HEIGHT // 2, MAP_HEIGHT - SCREEN_HEIGHT))

    # Framerate
    clock.tick(60)

    # Drawing the game
    screen.fill((0, 0, 0))  # Black background
    screen.blit(map_surface, (0, 0), camera)  # Draw the portion of the map within the camera view
    draw_stars(screen, white_stars, SCREEN_WIDTH, SCREEN_HEIGHT, (parallax_offset_x * 2, parallax_offset_y * 2))
    draw_stars(screen, purple_stars, SCREEN_WIDTH, SCREEN_HEIGHT, (parallax_offset_x * 3, parallax_offset_y * 3))
    draw_stars(screen, blue_stars, SCREEN_WIDTH, SCREEN_HEIGHT, (parallax_offset_x * 4, parallax_offset_y * 4))

    for orbit_radius in orbits:
        pygame.draw.circle(map_surface, (255, 255, 255), (map_center_x, map_center_y), orbit_radius, 1)

    for planet in planets:
        planet.draw(map_surface)

    animated_cargoship.update()
    spaceship_frame = animated_cargoship.get_frame(current_direction)
    #screen.blit(spaceship_frame, (x_position * TILE_SIZE, y_position * TILE_SIZE))
    screen.blit(spaceship_frame, (x_position * TILE_SIZE - camera.x, y_position * TILE_SIZE - camera.y))
    
    pygame.display.flip()  # Update the display
    print(f"Ship position: ({x_position}, {y_position}), Camera position: ({camera.x}, {camera.y})")
pygame.quit()