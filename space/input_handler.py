import pygame

def handle_movement(event, x_position, y_position, grid_size):
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

    return x_position, y_position

def determine_direction(x_position, y_position, previous_x, previous_y):
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

    return new_direction