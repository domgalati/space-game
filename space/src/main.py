# main.py
import pygame
from util.config import SCREEN_WIDTH, SCREEN_HEIGHT, TILE_SIZE
from modes.star_system_mode.star_system_mode import StarSystemMode
from modes.planetary_mode.planetary_mode import PlanetaryMode
from entities.player import Player

pygame.init()
pygame.font.init()  # Initialize the font module


screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Space Game")
clock = pygame.time.Clock()

### DEBUG LOAD ###
# These variables only exist to load directly into planetary mode when coding.
from modes.star_system_mode.star_systems import StarSystem
selected_planet = StarSystem(f'space/star_systems/sol.json').planets[0]
#### END OF DEBUG LOAD ###

player = Player()
star_system_mode = StarSystemMode(player, "sol")
planetary_mode = PlanetaryMode(selected_planet, player, screen)
current_mode = star_system_mode


running = True
while running:
    dt = clock.tick(60)  
    events = pygame.event.get()
    for event in events:
        if event.type == pygame.QUIT:
            running = False
    
    if isinstance(current_mode, StarSystemMode):
        current_mode.update(events)
        if current_mode.landing_requested:  # Check if landing was requested
            selected_planet = current_mode.get_selected_planet()  # Implement this method in StarSystemMode
            player = current_mode.get_player()  # Get the player object, implement this in StarSystemMode
            current_mode = PlanetaryMode(selected_planet, player, screen)
    elif isinstance(current_mode, PlanetaryMode):
        current_mode.update(events)
        current_mode.map_manager.update_animations(dt)
        if current_mode.switch_to_star_system_mode:
            current_mode = star_system_mode  # Switch back to StarSystemMode
            star_system_mode.landing_requested = False
            continue  # Skip drawing and immediately continue to the next loop iteration
    
    current_mode.draw(screen)

    pygame.display.flip()
    #clock.tick(60)


pygame.quit()
