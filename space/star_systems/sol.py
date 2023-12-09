import pygame
import math
from pygame.locals import Rect
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from nightsky import generate_stars, draw_stars
from sprite_animation import AnimatedSprite
from config import SCREEN_WIDTH, SCREEN_HEIGHT
from input_handler import handle_movement, determine_direction, update_parallax

# Initialize Pygame
pygame.init()
pygame.key.set_repeat(50, 200)  # 1 millisecond delay, 10 milliseconds interval

# Constants
TILE_SIZE = 24
MAP_WIDTH, MAP_HEIGHT = SCREEN_WIDTH * 8, SCREEN_HEIGHT * 8 # Map Size Constants

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
planet_image = pygame.image.load('space/img/planet.png')
def calculate_orbit_positions(center_x, center_y, orbit_radii, num_planets_per_orbit):
    planets = []
    for radius, num_planets in zip(orbit_radii, num_planets_per_orbit):
        for i in range(num_planets):
            angle = 2 * math.pi * i / num_planets  # Angle in radians
            x = center_x + int(radius * math.cos(angle))
            y = center_y + int(radius * math.sin(angle))
            planets.append((x, y))
    return planets

# Define the number of planets in each orbit and the radius of each orbit
num_planets_per_orbit = [4, 5, 6]  # Number of planets in each orbit
orbit_radii = [300, 500, 700]  # Radius of each orbit in pixels

# Calculate the orbit positions
planets = calculate_orbit_positions(map_center_x, map_center_y, orbit_radii, num_planets_per_orbit)

# planets = [
#     # Example planet positions
#     (0, 0),
#     (100,300),
#     (200, 100),
#     (400, 100),
#     (600, 300),
#     (8640, 5670),
#     # Add more planets as needed
# ]

# Function to draw planets
def draw_planets(surface, planets, planet_image):
    for planet_pos in planets:
        surface.blit(planet_image, planet_pos)

map_surface = pygame.Surface((MAP_WIDTH, MAP_HEIGHT)) # Create a surface for the map
# Initialize ship position at the center of the map
x_position = map_center_x // TILE_SIZE
y_position = map_center_y // TILE_SIZE


draw_planets(map_surface, planets, planet_image) # Drawing the planets on the map surface


# #####################
# Cargo Ship properties
cargo_sheet = 'space/img/cargo6frame.png'
frame_dimensions = (48, 48)  # Width and height of each frame
num_frames = 6  # Total number of frames in the sprite sheet
animated_cargoship = AnimatedSprite(cargo_sheet, frame_dimensions, num_frames)
current_direction = "southeast"


#############
##   DEBUG ##

def draw_grid(surface, tile_size, map_width, map_height, color=(255, 255, 255)):
    # Draw vertical lines
    for x in range(0, map_width, tile_size):
        pygame.draw.line(surface, color, (x, 0), (x, map_height))

    # Draw horizontal lines
    for y in range(0, map_height, tile_size):
        pygame.draw.line(surface, color, (0, y), (map_width, y))

## //DEBUG ##
#############

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
            #x_position, y_position = handle_movement(event, x_position, y_position, grid_size)
            x_position, y_position = handle_movement(x_position, y_position, grid_size)

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

    # Calculate camera position to center on the ship, with boundaries
    camera_center_x = x_position * TILE_SIZE + TILE_SIZE // 2
    camera_center_y = y_position * TILE_SIZE + TILE_SIZE // 2

    # Update camera position based on spaceship position
    camera.x = max(0, min(camera_center_x - SCREEN_WIDTH // 2, MAP_WIDTH - SCREEN_WIDTH))
    camera.y = max(0, min(camera_center_y - SCREEN_HEIGHT // 2, MAP_HEIGHT - SCREEN_HEIGHT))
    # Keep the camera within bounds of the map
   # camera.clamp_ip(Rect(0, 0, MAP_WIDTH, MAP_HEIGHT))
    
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
    #screen.blit(spaceship_frame, (x_position * TILE_SIZE, y_position * TILE_SIZE))
    screen.blit(spaceship_frame, (x_position * TILE_SIZE - camera.x, y_position * TILE_SIZE - camera.y))

    ###########
    ## DEBUG ##
    #draw_grid(screen, TILE_SIZE, MAP_WIDTH, MAP_HEIGHT)
    ## DEBUG ##
    ###########

    
    pygame.display.flip()  # Update the display
    print(f"Ship position: ({x_position}, {y_position}), Camera position: ({camera.x}, {camera.y})")
pygame.quit()

