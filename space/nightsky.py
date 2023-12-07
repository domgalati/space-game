import random
import pygame
from config import SCREEN_WIDTH, SCREEN_HEIGHT

"""
generate_stars():
Generates a list of stars with randomized attributes. 
Args:
    num_stars (int): The number of stars to be generated.
    screen_width (int): The width of the screen.
    screen_height (int): The height of the screen.
    size_options (list): A list of size options for the stars.
    color (tuple): An RGB color tuple.
Returns:
    List[Tuple]: A list of tuples where each tuple represents a star and contains its x, y 
                 coordinates, size, color, and original position.
"""
def generate_stars(num_stars, screen_width, screen_height, size_options, color):
    stars = []
    for _ in range(num_stars):
        x = random.randint(0, screen_width)
        y = random.randint(0, screen_height)
        size = random.choice(size_options)
        original_pos = (x, y)
        stars.append((x, y, size, color, original_pos))
    return stars


"""
Draws stars on a given screen.
Args:
    screen (pygame.Surface): The surface on which to draw the stars.
    stars (List[Tuple]): A list of tuples where each tuple represents a star and contains its 
                         x, y coordinates, size, color, and original position.
    screen_width (int): The width of the screen.
    screen_height (int): The height of the screen.
    offset (tuple, optional): A tuple containing x and y offset for parallax effect, defaults to (0, 0).
"""
def draw_stars(screen, stars, screen_width, screen_height, offset=(0, 0)):
    for star in stars:
        x, y, size, color, original_pos = star
        shifted_x = (x - offset[0]) % screen_width
        shifted_y = (y - offset[1]) % screen_height
        rect = pygame.Rect(shifted_x, shifted_y, size, size)
        pygame.draw.rect(screen, color, rect)