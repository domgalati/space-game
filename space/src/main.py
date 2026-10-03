# main.py
import pygame
from pygame._sdl2.video import WINDOWPOS_CENTERED, Window
from util.config import SCREEN_WIDTH, SCREEN_HEIGHT
from modes.star_system_mode.star_system_mode import StarSystemMode
from modes.planetary_mode.planetary_mode import PlanetaryMode
from entities.player import Player
from world.world_state import WorldState

STARTING_CREDITS = 1500
STARTING_SYSTEM = "sol"
# Skip flight and open on the system's first planet. Off for a normal new run.
DEBUG_START_ON_PLANET = False
START_FULLSCREEN = False
# Sensor test drones that wander near the start and ping. A debug aid until privateers exist.
DEBUG_DRONES = 0
# Privateers patrolling near the start. They hunt and engage but can't shoot until combat exists.
DEBUG_PRIVATEERS = 0
FULLSCREEN_KEY = pygame.K_F11  # switches between fullscreen and a window


def new_run():
    player = Player()
    player.currency = STARTING_CREDITS
    return player, WorldState()


def open_display(fullscreen):
    """SCALED keeps the 1080x720 canvas and stretches it to the monitor or the window.

    The window can be resized; the picture keeps its shape.
    """
    flags = pygame.SCALED | pygame.RESIZABLE | (pygame.FULLSCREEN if fullscreen else 0)
    return pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), flags)


def toggle_fullscreen(fullscreen):
    """Flip fullscreen in place. SDL cannot build a second SCALED renderer, so set_mode
    is not called again; a window comes back at 1080x720, centred, instead of monitor size."""
    try:
        pygame.display.toggle_fullscreen()
    except pygame.error:
        return fullscreen  # some video drivers cannot switch; stay as we are
    if fullscreen:
        restore_window()
    return not fullscreen


def restore_window():
    """1080x720 and centred. SCALED alone may pick the monitor size or a 2x multiple."""
    window = Window.from_display_module()
    window.size = (SCREEN_WIDTH, SCREEN_HEIGHT)
    window.position = WINDOWPOS_CENTERED


def main():
    pygame.init()
    pygame.font.init()

    fullscreen = START_FULLSCREEN
    screen = open_display(fullscreen)
    if not fullscreen:
        restore_window()
    pygame.display.set_caption("Space Game")
    clock = pygame.time.Clock()

    player, world_state = new_run()
    star_system_mode = StarSystemMode(player, STARTING_SYSTEM, world_state)
    star_system_mode.spawn_test_drones(DEBUG_DRONES)
    star_system_mode.spawn_test_privateers(DEBUG_PRIVATEERS)

    if DEBUG_START_ON_PLANET:
        current_mode = PlanetaryMode(
            star_system_mode.selected_system.planets[0], player, screen, world_state
        )
    else:
        current_mode = star_system_mode

    running = True
    while running:
        dt = clock.tick(60)
        events = []
        for event in pygame.event.get():
            if event.type == pygame.KEYDOWN and event.key == FULLSCREEN_KEY:
                fullscreen = toggle_fullscreen(fullscreen)
                continue
            events.append(event)
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
