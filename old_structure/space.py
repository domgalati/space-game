import pygame

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


x_velocity, y_velocity = 0, 0
acceleration = 1  # Adjust this value for quicker or slower acceleration
deceleration = 0.95  # Adjust this value for quicker or slower deceleration


running = True
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    # Game logic goes here
    keys = pygame.key.get_pressed()
    # Horizontal Movement
    if keys[pygame.K_KP4]:
        x_velocity -= acceleration
    elif keys[pygame.K_KP6]:
        x_velocity += acceleration
    else:
        x_velocity *= deceleration  # Slow down when no key is pressed
    
    # Vertical Movement
    if keys[pygame.K_KP8]:
        y_velocity -= acceleration
    elif keys[pygame.K_KP2]:
        y_velocity += acceleration
    else:
        y_velocity *= deceleration  # Slow down when no key is pressed
    
    # Diagonal Movement
    if keys[pygame.K_KP1]:
        x_velocity -= acceleration
        y_velocity += acceleration
    elif keys[pygame.K_KP3]:
        x_velocity += acceleration
        y_velocity += acceleration
    elif keys[pygame.K_KP7]:
        x_velocity -= acceleration
        y_velocity -= acceleration
    elif keys[pygame.K_KP9]:
        x_velocity += acceleration
        y_velocity -= acceleration

    x_position += x_velocity
    y_position += y_velocity

    # Keep the spaceship within the bounds of the screen
    x_position = max(0, min(x_position, SCREEN_WIDTH - TILE_SIZE))
    y_position = max(0, min(y_position, SCREEN_HEIGHT - TILE_SIZE))

    clock.tick(60)
    
    # Drawing the game
    screen.fill((0, 0, 0))  # Black background
    screen.blit(spaceship_img, (x_position, y_position))

    pygame.display.flip()  # Update the display

pygame.quit()
