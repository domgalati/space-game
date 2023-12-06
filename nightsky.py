import random
import pygame

SCREEN_WIDTH, SCREEN_HEIGHT = 640, 480 

def generate_stars(num_stars, screen_width, screen_height, size_options, color):
    stars = []
    for _ in range(num_stars):
        x = random.randint(0, screen_width)
        y = random.randint(0, screen_height)
        size = random.choice(size_options)
        original_pos = (x, y)
        stars.append((x, y, size, color, original_pos))
    return stars

def draw_stars(screen, stars):
    for star in stars:
        rect = pygame.Rect(star[0], star[1], star[2], star[2])  # Create a square rect
        pygame.draw.rect(screen, star[3], rect)

def update_star_positions(stars, shift_x, shift_y, parallax_factor, screen_width, screen_height):
    updated_stars = []
    for star in stars:
        original_x, original_y = star[4]
        new_x = (original_x + shift_x * parallax_factor) % screen_width
        new_y = (original_y + shift_y * parallax_factor) % screen_height

        # Create a new tuple with the updated position and the same size, color, and original position
        updated_star = (new_x, new_y, star[2], star[3], star[4])
        updated_stars.append(updated_star)
    return updated_stars