from collections import defaultdict

import pygame
import pytest

from entities.player import Player
from util.keys import held_direction
from world.world_state import WorldState


def held(*keys):
    pressed = defaultdict(bool)
    for key in keys:
        pressed[key] = True
    return pressed


def test_held_direction_reads_arrows_and_numpad_and_cancels_opposites():
    assert held_direction(held()) == (0, 0)
    assert held_direction(held(pygame.K_LEFT, pygame.K_UP)) == (-1, -1)
    assert held_direction(held(pygame.K_KP6, pygame.K_KP2)) == (1, 1)
    assert held_direction(held(pygame.K_LEFT, pygame.K_KP4)) == (-1, 0)  # same way twice is one step
    assert held_direction(held(pygame.K_LEFT, pygame.K_RIGHT)) == (0, 0)


def test_numpad_diagonals_win_over_arrow_chords():
    assert held_direction(held(pygame.K_KP9, pygame.K_LEFT, pygame.K_DOWN)) == (1, -1)


def test_flight_steps_are_paced_on_the_modes_clock(monkeypatch):
    from modes.star_system_mode.input_handler import InputHandler

    monkeypatch.setattr(pygame.key, "get_pressed", lambda: held(pygame.K_RIGHT))
    handler = InputHandler()
    assert handler.handle_movement(5, 5, (10, 10), now=0.0) == (6, 5)  # the first press steps at once
    assert handler.handle_movement(6, 5, (10, 10), now=0.1) == (6, 5)  # still cooling down
    assert handler.handle_movement(6, 5, (10, 10), now=0.3) == (7, 5)
    assert handler.handle_movement(9, 5, (10, 10), now=0.6) == (9, 5)  # the map edge holds


@pytest.fixture
def game():
    from game import Game

    pygame.init()
    pygame.display.set_mode((1, 1))
    return Game(Player(), WorldState(), "sol")


def dockable(game, place):
    system = game.mode.selected_system
    return next(body for body in [*system.planets, *system.objects] if body.id == place)


def test_docking_lands_and_departing_resumes_the_same_flight(game):
    from modes.planetary_mode.planetary_mode import PlanetaryMode

    flight = game.mode
    terramonta = dockable(game, "sol/terramonta")
    flight.request_landing(terramonta)
    game.update([], 1 / 60)
    assert isinstance(game.mode, PlanetaryMode)
    assert game.player.location.body == "sol/terramonta"

    game.mode.return_to_star_system_mode()  # what the docking terminal's "depart" does
    game.update([], 1 / 60)
    assert game.mode is flight
    assert game.player.location.body is None
    assert flight.nav.is_charted(terramonta)


def test_a_mode_with_nowhere_to_go_stays(game):
    flight = game.mode
    game.update([], 1 / 60)
    assert game.mode is flight
    assert flight.elapsed == pytest.approx(1 / 60)


def test_ashore_the_player_walks_and_interacts_in_tiles(game):
    from modes.planetary_mode.interaction_manager import _cardinal_neighbors

    game.mode.request_landing(dockable(game, "sol/nexum-astra"))
    game.update([], 1 / 60)
    ashore = game.mode
    start = ashore.player_tile
    assert all(isinstance(c, int) for c in start)

    ground = ashore.ground
    beside_terminal = next(
        tile for tile in ground.walkable_tiles()
        if ground.free(tile)
        and any(ashore.interaction_manager.object_at(t) == "Docking Terminal" for t in _cardinal_neighbors(tile))
    )
    ashore.player_tile = beside_terminal
    ashore.interaction_manager.interact(ashore.player_tile)
    assert ashore.terminal is not None and ashore.terminal.terminal_type == "docking"

    ashore.player_tile = start
    ashore.terminal = None
    stepped = next((d for d in ((1, 0), (-1, 0), (0, 1), (0, -1)) if ashore._try_move(*d)), None)
    assert stepped and ashore.player_tile == (start[0] + stepped[0], start[1] + stepped[1])
