import pygame
from util.config import SCREEN_WIDTH, SCREEN_HEIGHT, TILE_SIZE

class UI_Planetary:
    def __init__(self):
        self.sidebar_width = 200
        self.sidebar_surface = pygame.Surface((self.sidebar_width, SCREEN_HEIGHT - 200))
        self.font = pygame.font.Font("space/assets/fonts/Modern Pixel.otf", 16)  # You can change the font and size
        self.player_stats = None

    def update_player_stats(self, player):
        self.player_stats = {
            "Currency": player.currency,
            "Health": player.health,
            "Energy": player.energy
        }

    def draw_sidebar(self):
        if self.player_stats:
            y_offset = 30  # Starting point for the first stat, adjust as needed
            for stat, value in self.player_stats.items():
                if stat == "Currency":
                    stat_text = f"{stat}: ${value}"
                else:
                    stat_text = f"{stat}: {value}"
                text_surface = self.font.render(stat_text, True, (255, 255, 255))
                self.sidebar_surface.blit(text_surface, (10, y_offset))  # Adjust the position as needed
                y_offset += 20  # Space between lines, adjust as needed