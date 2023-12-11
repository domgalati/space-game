import pygame
from config import SCREEN_WIDTH, SCREEN_HEIGHT
from input_handler import handle_movement, determine_direction, update_parallax
from nightsky import initialize_stars, draw_stars, PARALLAX_FACTOR, PARALLAX_DAMPING_FACTOR, VELOCITY_THRESHOLD
from sprite_animation import AnimatedSprite
from star_systems import StarSystem

pygame.init()
pygame.key.set_repeat(50, 200)

# Constants
TILE_SIZE = 24

screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Space Game")
clock = pygame.time.Clock()

sol_system = StarSystem('space/star_systems/sol.json')
grid_size = (sol_system.MAP_WIDTH // TILE_SIZE, sol_system.MAP_HEIGHT // TILE_SIZE)
white_stars, purple_stars, blue_stars = initialize_stars(SCREEN_WIDTH, SCREEN_HEIGHT)
map_center_x = sol_system.MAP_WIDTH // 2
map_center_y = sol_system.MAP_HEIGHT // 2

cargo_sheet = 'space/img/cargo6frame.png'
frame_dimensions = (48, 48)
num_frames = 6
animated_cargoship = AnimatedSprite(cargo_sheet, frame_dimensions, num_frames)
current_direction = "southeast"
x_position = map_center_x // TILE_SIZE
y_position = map_center_y // TILE_SIZE
previous_x, previous_y = x_position, y_position
parallax_offset_x, parallax_offset_y = 0, 0
parallax_velocity_x, parallax_velocity_y = 0, 0
camera = pygame.Rect(0, 0, SCREEN_WIDTH, SCREEN_HEIGHT)

running = True
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.KEYDOWN:
            x_position, y_position = handle_movement(x_position, y_position, grid_size)

    new_direction = determine_direction(x_position, y_position, previous_x, previous_y)
    if new_direction:
        current_direction = new_direction

    parallax_offset_x, parallax_offset_y, parallax_velocity_x, parallax_velocity_y = update_parallax(
        x_position, y_position, previous_x, previous_y,
        parallax_offset_x, parallax_offset_y, parallax_velocity_x, parallax_velocity_y,
        PARALLAX_FACTOR, PARALLAX_DAMPING_FACTOR, VELOCITY_THRESHOLD
    )

    previous_x, previous_y = x_position, y_position
    camera_center_x = x_position * TILE_SIZE + TILE_SIZE // 2
    camera_center_y = y_position * TILE_SIZE + TILE_SIZE // 2
    camera.x = max(0, min(camera_center_x - SCREEN_WIDTH // 2, sol_system.MAP_WIDTH - SCREEN_WIDTH))
    camera.y = max(0, min(camera_center_y - SCREEN_HEIGHT // 2, sol_system.MAP_HEIGHT - SCREEN_HEIGHT))

    clock.tick(60)
    screen.fill((0, 0, 0))
    sol_system.draw(screen, camera)
    draw_stars(screen, white_stars, SCREEN_WIDTH, SCREEN_HEIGHT, (parallax_offset_x * 2, parallax_offset_y * 2))
    draw_stars(screen, purple_stars, SCREEN_WIDTH, SCREEN_HEIGHT, (parallax_offset_x * 3, parallax_offset_y * 3))
    draw_stars(screen, blue_stars, SCREEN_WIDTH, SCREEN_HEIGHT, (parallax_offset_x * 4, parallax_offset_y * 4))

    animated_cargoship.update()
    spaceship_frame = animated_cargoship.get_frame(current_direction)
    screen.blit(spaceship_frame, (x_position * TILE_SIZE - camera.x, y_position * TILE_SIZE - camera.y))

    pygame.display.flip()
    print(f"Ship position: ({x_position}, {y_position}), Camera position: ({camera.x}, {camera.y})")

pygame.quit()
