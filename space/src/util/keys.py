"""Movement keys, shared by every mode that moves something a tile at a time.

Arrows and the numpad move in eight directions. Numpad diagonals win over everything else,
so KP7/9/1/3 stay distinct from arrow chords; opposite keys cancel out.
"""
import pygame

DIAGONALS = {
    pygame.K_KP7: (-1, -1),
    pygame.K_KP9: (1, -1),
    pygame.K_KP1: (-1, 1),
    pygame.K_KP3: (1, 1),
}
LEFT = (pygame.K_LEFT, pygame.K_KP4)
RIGHT = (pygame.K_RIGHT, pygame.K_KP6)
UP = (pygame.K_UP, pygame.K_KP8)
DOWN = (pygame.K_DOWN, pygame.K_KP2)


def held_direction(keys):
    """(dx, dy), each -1, 0 or 1, from the movement keys held in ``keys`` (pygame.key.get_pressed())."""
    for key, step in DIAGONALS.items():
        if keys[key]:
            return step
    dx = any(keys[k] for k in RIGHT) - any(keys[k] for k in LEFT)
    dy = any(keys[k] for k in DOWN) - any(keys[k] for k in UP)
    return dx, dy
