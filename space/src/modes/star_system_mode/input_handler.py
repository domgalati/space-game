import math

import pygame

from util.keys import held_direction


class InputHandler:
    """Paces held keys in flight: one step or wait per cooldown, timed on the mode's clock."""

    def __init__(self):
        self.last_movement_time = -math.inf
        self.movement_cooldown = 0.2  # seconds

    def handle_movement(self, ship_x_position, ship_y_position, grid_size, now):
        """The ship's tile after any held movement key; `now` is the mode's clock in seconds."""
        dx, dy = held_direction(pygame.key.get_pressed())
        if not (dx or dy) or now - self.last_movement_time <= self.movement_cooldown:
            return ship_x_position, ship_y_position
        self.last_movement_time = now
        return (
            min(grid_size[0] - 1, max(0, ship_x_position + dx)),
            min(grid_size[1] - 1, max(0, ship_y_position + dy)),
        )

    def handle_wait(self, key, cooldown, now):
        """True when `key` should pass a turn in place; holding it repeats at cruise pace."""
        if pygame.key.get_pressed()[key] and now - self.last_movement_time > cooldown:
            self.last_movement_time = now
            return True
        return False

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

## It actually DOES make sense to have this here. Parallax is tied to movement.
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
