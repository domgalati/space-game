import random
import pygame

SCREEN_WIDTH, SCREEN_HEIGHT = 1080, 720

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


