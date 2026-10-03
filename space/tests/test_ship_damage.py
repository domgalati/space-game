import pygame
import pytest

from entities.player import SHIELD_RECHARGE, SHIELD_RECHARGE_DOWN, Player, Ship
from modes.star_system_mode.shield_fx import BLOCK, BLOCKS, shield_surface
from modes.star_system_mode.star_systems import HEAT_MAX, HEAT_START, SUN_RADIUS, StarSystem
from util.config import TILE_SIZE
from util.economy import trade
from util.sprite_animation import TINT_LEVELS


@pytest.fixture(scope="module", autouse=True)
def _display():
    pygame.init()
    pygame.display.set_mode((1, 1))
    yield


def test_raised_shield_soaks_damage_before_the_hull():
    ship = Ship()
    ship.shield_up = True
    ship.shield = 5
    assert ship.take_damage(8) == (5, 3)
    assert (ship.shield, ship.hull) == (0, 97)


def test_lowered_shield_lets_everything_through():
    ship = Ship()
    assert ship.take_damage(10) == (0, 10)
    assert ship.shield == ship.max_shield


def test_hull_stops_at_zero():
    ship = Ship()
    ship.take_damage(500)
    assert ship.hull == 0


def test_shield_recharges_only_on_clean_turns():
    ship = Ship()
    ship.shield = 50
    ship.take_damage(1)
    ship.end_turn()
    assert ship.shield == 50
    ship.end_turn()
    assert ship.shield == 50 + SHIELD_RECHARGE_DOWN
    ship.shield = ship.max_shield
    ship.end_turn()
    assert ship.shield == ship.max_shield


@pytest.fixture(scope="module")
def sol():
    return StarSystem("space/star_systems/sol.json")


def test_heat_is_zero_on_the_outskirts_and_peaks_at_the_core(sol):
    cx, cy = sol.map_center_x, sol.map_center_y
    assert sol.heat_at((cx, cy)) == HEAT_MAX
    assert sol.heat_at((cx + SUN_RADIUS * HEAT_START, cy)) == 0
    assert sol.heat_at((cx + SUN_RADIUS * 0.9, cy)) == 0
    assert 0 < sol.heat_at((cx + SUN_RADIUS * 0.4, cy)) < sol.heat_at((cx + SUN_RADIUS * 0.2, cy))


@pytest.fixture
def mode():
    from modes.star_system_mode.star_system_mode import StarSystemMode

    pygame.font.init()
    return StarSystemMode(Player(), "sol")


def park(mode, point):
    mode.x_position = int(point[0]) // TILE_SIZE
    mode.y_position = int(point[1]) // TILE_SIZE


def test_a_turn_at_the_core_burns_the_shield_then_the_hull(mode):
    system = mode.selected_system
    ship = mode.player.ship
    park(mode, (system.map_center_x, system.map_center_y))
    mode.set_shield(True)
    ship.shield = 3
    mode.spend_turns(1)
    assert ship.shield == 0
    assert ship.hull == pytest.approx(ship.max_hull - (system.heat_at(mode.ship_center()) - 3))
    assert mode.clock.turn == 1


def test_a_turn_in_open_space_recharges(mode):
    ship = mode.player.ship
    ship.shield = 10
    mode.spend_turns(1)
    assert ship.shield == 10 + SHIELD_RECHARGE_DOWN


def test_a_lowered_shield_recharges_faster_than_a_raised_one():
    raised, lowered = Ship(), Ship()
    raised.shield_up = True
    raised.shield = lowered.shield = 0
    raised.end_turn()
    lowered.end_turn()
    assert raised.shield == SHIELD_RECHARGE < lowered.shield == SHIELD_RECHARGE_DOWN


def test_hull_tint_deepens_with_damage(mode):
    ship = mode.player.ship
    assert mode.hull_tint(0) == 0
    ship.hull = ship.max_hull * 0.5
    assert 0 < mode.hull_tint(0) < TINT_LEVELS - 1
    ship.hull = ship.max_hull * 0.1
    assert {mode.hull_tint(0), mode.hull_tint(250)} == {TINT_LEVELS - 1, TINT_LEVELS - 2}


def test_shield_shell_is_blocky_and_fades_with_charge():
    full = shield_surface(1.0, 0)
    assert full.get_size() == (BLOCKS * BLOCK, BLOCKS * BLOCK)
    rim = full.get_at((BLOCKS * BLOCK // 2, 2)).a
    assert rim > shield_surface(0.3, 0).get_at((BLOCKS * BLOCK // 2, 2)).a
    assert full.get_at((0, 0)).a == 0


def test_repair_charges_per_point_and_stops_at_max():
    player = Player()
    player.currency = 1000
    player.ship.hull = 90
    trade.repair(player)
    assert player.ship.hull == player.ship.max_hull
    assert player.currency == 1000 - 10 * trade.REPAIR_PRICE
    assert "already" in trade.repair(player)
