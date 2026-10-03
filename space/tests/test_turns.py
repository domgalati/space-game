import pygame
import pytest

from entities.player import Player
from util.config import TILE_SIZE
from util.turns import Ticker, TurnClock


class Counter:
    def __init__(self, speed, log=None, name=""):
        self.speed = speed
        self.turns = 0
        self.log = log
        self.name = name

    def take_turn(self):
        self.turns += 1
        if self.log is not None:
            self.log.append(self.name)


def test_speed_sets_how_often_an_actor_acts():
    clock = TurnClock()
    slow, normal, fast = Counter(50), Counter(100), Counter(200)
    for actor in (slow, normal, fast):
        clock.add(actor)
    clock.advance(4)
    assert (slow.turns, normal.turns, fast.turns) == (2, 4, 8)
    assert clock.turn == 4


def test_half_turns_add_up():
    clock = TurnClock()
    normal = Counter(100)
    clock.add(normal)
    clock.advance(0.5)
    assert normal.turns == 0
    clock.advance(0.5)
    assert normal.turns == 1


def test_actors_act_in_time_order_and_ties_go_in_the_order_added():
    log = []
    clock = TurnClock()
    clock.add(Counter(100, log, "normal"))
    clock.add(Counter(200, log, "fast"))
    clock.advance(1)
    assert log == ["fast", "normal", "fast"]


def test_an_actor_can_leave_mid_turn():
    clock = TurnClock()
    gone = Counter(100)
    clock.add(Ticker(lambda: clock.remove(gone), speed=200))
    clock.add(gone)
    clock.advance(3)
    assert gone.turns == 0


@pytest.fixture
def mode():
    from modes.star_system_mode.star_system_mode import StarSystemMode

    pygame.init()
    pygame.display.set_mode((1, 1))
    pygame.font.init()
    return StarSystemMode(Player(), "sol")


def test_boosted_moves_take_half_a_turn_and_reserve_moves_take_two(mode):
    from modes.star_system_mode.star_system_mode import WAIT_TURNS

    assert mode.move_turns() == 1
    mode.boosting = True
    assert mode.move_turns() == 0.5
    mode.player.ship.fuel = 0
    assert mode.move_turns() == 2
    assert WAIT_TURNS == 1


def test_boosting_through_the_sun_halves_the_heat_per_tile(mode):
    system = mode.selected_system
    ship = mode.player.ship
    mode.x_position = system.map_center_x // TILE_SIZE
    mode.y_position = system.map_center_y // TILE_SIZE
    mode.spend_turns(0.5)
    assert ship.hull == ship.max_hull
    mode.spend_turns(0.5)
    assert ship.hull < ship.max_hull


def test_hull_failure_tows_the_ship_home_repaired_for_a_fee(mode):
    from modes.star_system_mode.star_system_mode import TOW_FEE

    system = mode.selected_system
    ship = mode.player.ship
    mode.player.currency = 1000
    mode.x_position = system.map_center_x // TILE_SIZE
    mode.y_position = system.map_center_y // TILE_SIZE
    ship.hull = 1
    mode.spend_turns(1)
    assert ship.hull == ship.max_hull
    assert mode.player.currency == 1000 - int(1000 * TOW_FEE)
    spawn = system.spawn_point()
    assert (mode.x_position, mode.y_position) == (int(spawn[0]) // TILE_SIZE, int(spawn[1]) // TILE_SIZE)
    assert "TOWED" in mode.events.latest()
