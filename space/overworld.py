import pygame
from nightsky import generate_stars, draw_stars
from sprite_animation import AnimatedSprite
from config import SCREEN_WIDTH, SCREEN_HEIGHT

# Initialize Pygame
pygame.init()

# Constants
#SCREEN_WIDTH, SCREEN_HEIGHT = 1080, 720  # Adjust as needed
TILE_SIZE = 24

# Set up the display
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("working title")

clock = pygame.time.Clock()

x_position, y_position = 0, 0
grid_size = (SCREEN_WIDTH // TILE_SIZE, SCREEN_HEIGHT // TILE_SIZE)

# Star properties
parallax_factor = 0.5  # Adjust this for the effect strength
parallax_offset_x, parallax_offset_y = 0, 0 # Initialize parallax offset variables
star_size_options = [1, 2, 3]  # Different sizes for variety
white_stars = generate_stars(100, SCREEN_WIDTH, SCREEN_HEIGHT, star_size_options, (255, 255, 255))
purple_stars = generate_stars(50, SCREEN_WIDTH, SCREEN_HEIGHT, star_size_options, (51, 0, 51))
blue_stars = generate_stars(75, SCREEN_WIDTH, SCREEN_HEIGHT, star_size_options, (190, 230, 255)) 

sprite_sheet_path = 'space/img/cargo6frame.png'
frame_dimensions = (48, 48)  # Width and height of each frame
num_frames = 6  # Total number of frames in the sprite sheet
animated_spaceship = AnimatedSprite(sprite_sheet_path, frame_dimensions, num_frames)
current_direction = "south"

#main loop
running = True
previous_x, previous_y = x_position, y_position # Initializing positions for paralax
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.KEYDOWN:
            # Horizontal and Vertical Movement
            if event.key == pygame.K_KP4:
                x_position = max(0, x_position - 1)
            elif event.key == pygame.K_KP6:
                x_position = min(grid_size[0] - 1, x_position + 1)
            if event.key == pygame.K_KP8:
                y_position = max(0, y_position - 1)
            elif event.key == pygame.K_KP2:
                y_position = min(grid_size[1] - 1, y_position + 1)

            # Diagonal Movement
            if event.key == pygame.K_KP1:
                x_position = max(0, x_position - 1)
                y_position = min(grid_size[1] - 1, y_position + 1)
            elif event.key == pygame.K_KP3:
                x_position = min(grid_size[0] - 1, x_position + 1)
                y_position = min(grid_size[1] - 1, y_position + 1)
            elif event.key == pygame.K_KP7:
                x_position = max(0, x_position - 1)
                y_position = max(0, y_position - 1)
            elif event.key == pygame.K_KP9:
                x_position = min(grid_size[0] - 1, x_position + 1)
                y_position = max(0, y_position - 1)

    # Determine the direction of movement for ship rotation
    new_direction = None
    if x_position > previous_x and y_position > previous_y:
        new_direction = "southeast"
    elif x_position > previous_x and y_position < previous_y:
        new_direction = "northeast"
    elif x_position < previous_x and y_position > previous_y:
        new_direction = "southwest"
    elif x_position < previous_x and y_position < previous_y:
        new_direction = "northwest"
    elif x_position > previous_x:
        new_direction = "east"
    elif x_position < previous_x:
        new_direction = "west"
    elif y_position > previous_y:
        new_direction = "south"
    elif y_position < previous_y:
        new_direction = "north"

    if new_direction is not None:
        current_direction = new_direction
    
    # Calculate parallax offset based on spaceship movement
    delta_x = (x_position - previous_x) * parallax_factor
    delta_y = (y_position - previous_y) * parallax_factor

    # Accumulate the offset
    parallax_offset_x += delta_x
    parallax_offset_y += delta_y

    # Update the previous position for the next iteration
    previous_x, previous_y = x_position, y_position

    # Keep the spaceship within the bounds of the screen
    x_position = max(0, min(x_position, SCREEN_WIDTH - TILE_SIZE))
    y_position = max(0, min(y_position, SCREEN_HEIGHT - TILE_SIZE))

    clock.tick(24)
    
    # Drawing the game
    screen.fill((0, 0, 0))  # Black background
    draw_stars(screen, white_stars, SCREEN_WIDTH, SCREEN_HEIGHT, (parallax_offset_x * 2, parallax_offset_y * 2))
    draw_stars(screen, purple_stars, SCREEN_WIDTH, SCREEN_HEIGHT, (parallax_offset_x * 3, parallax_offset_y * 3))
    draw_stars(screen, blue_stars, SCREEN_WIDTH, SCREEN_HEIGHT, (parallax_offset_x * 4, parallax_offset_y * 4))
    animated_spaceship.update()
    spaceship_frame = animated_spaceship.get_frame(current_direction)
    screen.blit(spaceship_frame, (x_position * TILE_SIZE, y_position * TILE_SIZE))
    pygame.display.flip()  # Update the display
    
pygame.quit()

