import random
import pygame

def generate_stars(num_stars, screen_width, screen_height, size_options, color):
    stars = []
    for _ in range(num_stars):
        x = random.randint(0, screen_width)
        y = random.randint(0, screen_height)
        size = random.choice(size_options)
        stars.append((x, y, size, color))
    return stars

def draw_stars(screen, stars):
    for star in stars:
        rect = pygame.Rect(star[0], star[1], star[2], star[2])  # Create a square rect
        pygame.draw.rect(screen, star[3], rect)


        test change