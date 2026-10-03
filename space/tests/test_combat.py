import math
import random

import pygame
import pytest

from entities.player import Player, Ship
from modes.star_system_mode.combat import BANDS, SCAN_RANGE, SHOT_COST, WEAPON_RANGE, band, fire
from modes.star_system_mode.privateers import ENGAGE, Privateer
from modes.star_system_mode.sensors import SIGNATURE_FIRING
from modes.star_system_mode.wrecks import WRECK_TURNS
from util.config import SCREEN_HEIGHT, SCREEN_WIDTH, TILE_SIZE
from world.factions import KILL_LAW_STANDING, KILL_SPONSOR_STANDING


class Fixed:
    """A stand-in rng whose rolls always come up `value`."""

    def __init__(self, value):
        self.value = value

    def random(self):
        return self.value

    def choice(self, items):
        return items[0]

    def randint(self, low, high):
        return low


HIT, MISS = Fixed(0.0), Fixed(0.999)


def test_hit_chance_and_damage_fall_off_with_range():
    chances = [band(reach)[0] for reach, *_ in BANDS]
    damages = [band(reach)[1] for reach, *_ in BANDS]
    assert chances == sorted(chances, reverse=True) and damages == sorted(damages, reverse=True)
    assert band(WEAPON_RANGE + 1) is None


def test_a_shot_spends_shield_charge_even_with_the_shield_down():
    shooter, target = Ship(), Ship()
    hit, to_shield, to_hull = fire(shooter, target, (0, 0), (50, 0), HIT)
    assert hit and shooter.shield == shooter.max_shield - SHOT_COST and shooter.hit_this_turn
    assert to_hull == band(50)[1]  # target's shield is down, so the hull takes it
    assert fire(shooter, target, (0, 0), (50, 0), MISS) == (False, 0, 0)


@pytest.fixture
def mode():
    from modes.star_system_mode.star_system_mode import StarSystemMode

    pygame.init()
    pygame.display.set_mode((1, 1))
    pygame.font.init()
    flight = StarSystemMode(Player(), "sol")
    flight.rng = HIT
    x, y = flight.map_center_x, flight.map_center_y + 15000  # open space, no patrol zone
    flight.x_position, flight.y_position = int(x) // TILE_SIZE, int(y) // TILE_SIZE
    flight.player.ship.shield_up = True  # loud enough to be seen, and to see
    return flight


def privateer(mode, dx, dy, kind="raider", sponsor="dominion"):
    x, y = mode.ship_center()
    ship = Privateer(kind, sponsor, (x + dx, y + dy), mode, rng=random.Random(4))
    mode.add_vessel(ship)
    return ship


def test_firing_hits_spends_a_turn_and_is_loud(mode):
    target = privateer(mode, 150, 0)
    target.ship.shield_up = False
    mode.player_fire()
    assert target.ship.hull == target.ship.max_hull - band(150)[1]
    assert mode.clock.turn == 1
    assert mode.player_signature() >= SIGNATURE_FIRING
    assert mode.player.ship.shield == mode.player.ship.max_shield - SHOT_COST  # no recharge on a firing turn


def test_you_cannot_fire_out_of_range_or_without_charge(mode):
    far = privateer(mode, WEAPON_RANGE + 60, 0)
    far.ship.shield_up = True  # loud enough to stay in sight past weapon range
    mode.target = far
    mode.player_fire()
    assert "OUT OF RANGE" in mode.notice[0] and mode.clock.turn == 0
    near = privateer(mode, 100, 0)
    mode.target = near
    mode.player.ship.shield = SHOT_COST - 1
    mode.player_fire()
    assert "CHARGE TOO LOW" in mode.notice[0] and mode.clock.turn == 0


def test_a_kill_leaves_a_wreck_and_moves_standing(mode):
    target = privateer(mode, 120, 0, kind="cutter")
    target.ship.hull, target.ship.shield = 1, 0
    mode.player_fire()
    assert target not in mode.vessels and len(mode.wrecks) == 1
    assert mode.player.reputation["dominion"] == KILL_SPONSOR_STANDING
    assert mode.player.reputation["assembly"] == KILL_LAW_STANDING
    assert mode.player.kill_log == [{"sponsor": "dominion", "kind": "cutter"}]
    assert "DESTROYED" in mode.notice[0]


def test_salvage_fills_the_hold_and_the_wreck_breaks_up(mode):
    target = privateer(mode, 120, 0)
    target.ship.hull, target.ship.shield = 1, 0
    mode.player_fire()
    (wreck,) = mode.wrecks
    goods = dict(wreck.cargo)
    credits_before = mode.player.currency
    mode.salvage(wreck)
    for good, quantity in goods.items():
        assert mode.player.ship.cargo.items[good] == quantity
    assert mode.player.currency > credits_before
    assert mode.salvage(wreck) == ["Nothing left worth taking."]
    mode.spend_turns(WRECK_TURNS)
    assert not mode.wrecks


def test_salvage_leaves_what_does_not_fit(mode):
    target = privateer(mode, 120, 0)
    target.ship.hull, target.ship.shield = 1, 0
    mode.player_fire()
    (wreck,) = mode.wrecks
    cargo = mode.player.ship.cargo
    cargo.add_item("Rocks", cargo.capacity - 1)
    lines = mode.salvage(wreck)
    assert any("No room" in line for line in lines) and not wreck.empty()


def test_privateers_telegraph_a_shot_a_turn_ahead(mode):
    raider = privateer(mode, 150, 0)
    mode.spend_turns(1)
    assert raider.state == ENGAGE and raider.intent[0] == "fire"
    assert mode.player.ship.shield == mode.player.ship.max_shield  # warned, not shot yet
    mode.spend_turns(1)
    assert mode.player.ship.shield < mode.player.ship.max_shield


def test_stepping_out_of_range_spoils_a_declared_shot(mode):
    raider = privateer(mode, 150, 0)
    mode.spend_turns(1)
    assert raider.intent[0] == "fire"
    mode.x_position -= (WEAPON_RANGE + 2 * TILE_SIZE) // TILE_SIZE  # jump out of range before it fires
    raider_charge = raider.ship.shield
    mode.spend_turns(1)
    assert raider.ship.shield >= raider_charge and mode.player.ship.hull == mode.player.ship.max_hull


def test_their_shots_drain_their_own_shield(mode):
    raider = privateer(mode, 150, 0, kind="cutter")
    mode.spend_turns(6)
    assert raider.ship.shield < SHOT_COST * 2  # a cutter's 30 charge is two shots


def test_scanning_reveals_intent_and_costs_a_turn(mode):
    raider = privateer(mode, 300, 0)
    mode.target = raider
    mode.player_scan()
    assert raider.scanned and mode.clock.turn == 1
    surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
    mode.handle_continuous_updates()
    mode.draw(surface)


def test_scans_reach_twenty_tiles(mode):
    far = privateer(mode, SCAN_RANGE + 50, 0)
    far.ship.shield_up = True  # loud enough to stay in sight past scan range
    mode.target = far
    mode.player_scan()
    assert not far.scanned and "TOO FAR" in mode.notice[0]


def test_tab_cycles_through_contacts_in_sight(mode):
    first, second = privateer(mode, 100, 0), privateer(mode, 200, 0)
    mode.target = None
    mode.cycle_target()
    assert mode.target is first
    mode.cycle_target()
    assert mode.target is second


def test_the_ship_computer_reads_and_salvages_a_wreck(mode):
    from modes.star_system_mode.scan_terminal import ScanTerminal

    target = privateer(mode, 120, 0)
    target.ship.hull, target.ship.shield = 1, 0
    mode.player_fire()
    (wreck,) = mode.wrecks
    terminal = ScanTerminal(wreck, mode)
    terminal.execute_command("scan")
    assert any("Dominion raider" in str(line) for line in terminal.output_buffer)
    terminal.execute_command("salvage")
    assert wreck.empty()
