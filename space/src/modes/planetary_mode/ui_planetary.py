import pygame
from util.config import SCREEN_WIDTH, SCREEN_HEIGHT, TILE_SIZE

class UI_Planetary:
    def __init__(self):
        self.sidebar_width = 200
        self.sidebar_surface = pygame.Surface((self.sidebar_width, SCREEN_HEIGHT - 200))

    def draw_sidebar(self):
        # Draw player stats and other relevant information
        # Add logic to display player stats
        pass