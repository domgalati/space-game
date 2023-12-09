import pygame

def handle_movement(ship_x_position, ship_y_position, grid_size):
    keys = pygame.key.get_pressed()
    if keys[pygame.K_KP4]:
        ship_x_position = max(0, ship_x_position - 1)
    elif keys[pygame.K_KP6]:
        ship_x_position = min(grid_size[0] - 1, ship_x_position + 1)
    if keys[pygame.K_KP8]:
        ship_y_position = max(0, ship_y_position - 1)
    elif keys[pygame.K_KP2]:
        ship_y_position = min(grid_size[1] - 1, ship_y_position + 1)
    # Diagonal Movement
    if keys[pygame.K_KP1]:
        ship_x_position = max(0, ship_x_position - 1)
        ship_y_position = min(grid_size[1] - 1, ship_y_position + 1)
    elif keys[pygame.K_KP3]:
        ship_x_position = min(grid_size[0] - 1, ship_x_position + 1)
        ship_y_position = min(grid_size[1] - 1, ship_y_position + 1)
    elif keys[pygame.K_KP7]:
        ship_x_position = max(0, ship_x_position - 1)
        ship_y_position = max(0, ship_y_position - 1)
    elif keys[pygame.K_KP9]:
        ship_x_position = min(grid_size[0] - 1, ship_x_position + 1)
        ship_y_position = max(0, ship_y_position - 1)
    return ship_x_position, ship_y_position

def determine_direction(ship_x_position, ship_y_position, previous_x, previous_y):
    new_direction = None
    if ship_x_position > previous_x and ship_y_position > previous_y:
        new_direction = "southeast"
    elif ship_x_position > previous_x and ship_y_position < previous_y:
        new_direction = "northeast"
    elif ship_x_position < previous_x and ship_y_position > previous_y:
        new_direction = "southwest"
    elif ship_x_position < previous_x and ship_y_position < previous_y:
        new_direction = "northwest"
    elif ship_x_position > previous_x:
        new_direction = "east"
    elif ship_x_position < previous_x:
        new_direction = "west"
    elif ship_y_position > previous_y:
        new_direction = "south"
    elif ship_y_position < previous_y:
        new_direction = "north"

    return new_direction

def update_parallax(ship_x_position, ship_y_position, previous_x, previous_y, parallax_offset_x, parallax_offset_y, parallax_velocity_x, parallax_velocity_y, parallax_factor, damping_factor, velocity_threshold):
    # Immediate change in position
    immediate_delta_x = (ship_x_position - previous_x) * parallax_factor
    immediate_delta_y = (ship_y_position - previous_y) * parallax_factor

    # Update velocities based on immediate movement
    parallax_velocity_x += immediate_delta_x
    parallax_velocity_y += immediate_delta_y

    # Apply damping to simulate inertia
    parallax_velocity_x *= damping_factor
    parallax_velocity_y *= damping_factor

    # Apply the minimum velocity threshold
    if abs(parallax_velocity_x) < velocity_threshold:
        parallax_velocity_x = 0
    if abs(parallax_velocity_y) < velocity_threshold:
        parallax_velocity_y = 0

    # Update parallax offsets using the velocity
    parallax_offset_x += parallax_velocity_x
    parallax_offset_y += parallax_velocity_y

    return parallax_offset_x, parallax_offset_y, parallax_velocity_x, parallax_velocity_y
