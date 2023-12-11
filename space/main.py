# main.py
import pygame
from config import SCREEN_WIDTH, SCREEN_HEIGHT, TILE_SIZE
from star_system_mode import StarSystemMode

pygame.init()

screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Space Game")
clock = pygame.time.Clock()

star_system_mode = StarSystemMode()

running = True
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
    
    clock.tick(60)
    star_system_mode.update()
    star_system_mode.draw(screen)
    pygame.display.flip()
    # ... other code ...

pygame.quit()
