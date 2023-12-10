import random
import pygame
from config import SCREEN_WIDTH, SCREEN_HEIGHT

PARALLAX_FACTOR = 0.5
PARALLAX_DAMPING_FACTOR = 0.95
VELOCITY_THRESHOLD = 0.1
STAR_SIZE_OPTIONS = [.5, 1, 2]

def initialize_stars(screen_width, screen_height):
    white_stars = generate_stars(100, screen_width, screen_height, STAR_SIZE_OPTIONS, (255, 255, 255))
    purple_stars = generate_stars(50, screen_width, screen_height, STAR_SIZE_OPTIONS, (51, 0, 51))
    blue_stars = generate_stars(75, screen_width, screen_height, STAR_SIZE_OPTIONS, (185, 217, 235))
    return white_stars, purple_stars, blue_stars

def generate_stars(num_stars, screen_width, screen_height, size_options, color):
    stars = []
    for _ in range(num_stars):
        x = random.randint(0, screen_width)
        y = random.randint(0, screen_height)
        size = random.choice(size_options)
        original_pos = (x, y)
        stars.append((x, y, size, color, original_pos))
    return stars

def draw_stars(screen, stars, screen_width, screen_height, offset=(0, 0)):
    for star in stars:
        x, y, size, color, original_pos = star
        shifted_x = (x - offset[0]) % screen_width
        shifted_y = (y - offset[1]) % screen_height
        rect = pygame.Rect(shifted_x, shifted_y, size, size)
        pygame.draw.rect(screen, color, rect)