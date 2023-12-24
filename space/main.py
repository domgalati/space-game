# main.py
import pygame
from config import SCREEN_WIDTH, SCREEN_HEIGHT, TILE_SIZE
from star_system_mode import StarSystemMode

pygame.init()
pygame.font.init()  # Initialize the font module


screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Space Game")
clock = pygame.time.Clock()

star_system_mode = StarSystemMode()

running = True
while running:
    events = pygame.event.get()
    for event in events:
        if event.type == pygame.QUIT:
            running = False
    
    star_system_mode.update(events)
    star_system_mode.draw(screen)
    
    pygame.display.flip()
    clock.tick(144)


pygame.quit()
