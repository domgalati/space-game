import pygame
from nightsky import generate_stars, draw_stars, update_star_positions

# Initialize Pygame
pygame.init()

# Constants
SCREEN_WIDTH, SCREEN_HEIGHT = 640, 480  # Adjust as needed
TILE_SIZE = 24

# Set up the display
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Spaceship Game")

clock = pygame.time.Clock()

spaceship_img = pygame.image.load('placeholder.png').convert_alpha()
spaceship_img = pygame.transform.scale(spaceship_img, (TILE_SIZE, TILE_SIZE))

x_position, y_position = 0, 0
grid_size = (SCREEN_WIDTH // TILE_SIZE, SCREEN_HEIGHT // TILE_SIZE)

# Star properties
star_size_options = [1, 2, 3]  # Different sizes for variety
white_stars = generate_stars(100, SCREEN_WIDTH, SCREEN_HEIGHT, star_size_options, (255, 255, 255))
purple_stars = generate_stars(50, SCREEN_WIDTH, SCREEN_HEIGHT, star_size_options, (51, 0, 51))
blue_stars = generate_stars(75, SCREEN_WIDTH, SCREEN_HEIGHT, star_size_options, (190, 230, 255)) 

running = True
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

    # Keep the spaceship within the bounds of the screen
    x_position = max(0, min(x_position, SCREEN_WIDTH - TILE_SIZE))
    y_position = max(0, min(y_position, SCREEN_HEIGHT - TILE_SIZE))

    shift_x = 0  # Calculate the background shift based on spaceship movement for paralax
    shift_y = 0  

    # Update star positions for each layer with different parallax factors
    update_star_positions(white_stars, shift_x, shift_y, 0.5)  # Less movement for distant layer
    update_star_positions(purple_stars, shift_x, shift_y, 0.3)  # Even less movement for further layer
    update_star_positions(blue_stars, shift_x, shift_y, 0.1)  # Minimal movement for the farthest layer

    clock.tick(60)
    
    # Drawing the game
    screen.fill((0, 0, 0))  # Black background
    draw_stars(screen, white_stars)
    draw_stars(screen, purple_stars)
    draw_stars(screen, blue_stars)
    screen.blit(spaceship_img, (x_position * TILE_SIZE, y_position * TILE_SIZE))
    pygame.display.flip()  # Update the display
    
pygame.quit()
