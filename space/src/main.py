# main.py
import pygame
from util.config import SCREEN_WIDTH, SCREEN_HEIGHT
from modes.star_system_mode.star_system_mode import StarSystemMode
from modes.planetary_mode.planetary_mode import PlanetaryMode
from entities.player import Player
from world.world_state import WorldState

STARTING_CREDITS = 1500
STARTING_SYSTEM = "sol"
# Skip flight and open on the system's first planet. Off for a normal new run.
DEBUG_START_ON_PLANET = False


def new_run():
    player = Player()
    player.currency = STARTING_CREDITS
    return player, WorldState()


def main():
    pygame.init()
    pygame.font.init()

    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("Space Game")
    clock = pygame.time.Clock()

    player, world_state = new_run()
    star_system_mode = StarSystemMode(player, STARTING_SYSTEM, world_state)

    if DEBUG_START_ON_PLANET:
        current_mode = PlanetaryMode(
            star_system_mode.selected_system.planets[0], player, screen, world_state
        )
    else:
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
            if current_mode.landing_requested:
                selected_planet = current_mode.get_selected_planet()
                player = current_mode.get_player()
                current_mode = PlanetaryMode(selected_planet, player, screen, world_state)
        elif isinstance(current_mode, PlanetaryMode):
            current_mode.update(events)
            current_mode.map_manager.update_animations(dt)
            if current_mode.switch_to_star_system_mode:
                star_system_mode.nav.chart(current_mode.planet.name)
                current_mode = star_system_mode
                star_system_mode.landing_requested = False
                continue

        current_mode.draw(screen)

        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    main()
