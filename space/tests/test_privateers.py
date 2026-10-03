import math
import random

import pygame
import pytest

from entities.player import Player
from modes.star_system_mode.privateers import (
    ARRIVED, BOOST_RESERVE, CLASSES, ENGAGE, ENGAGE_RANGE, HUNT, PATROL, RETREAT, SEARCH, SEARCH_TURNS,
    Privateer, search_turns,
)
from util.config import SCREEN_HEIGHT, SCREEN_WIDTH, TILE_SIZE
from world.factions import WAVE_BY


@pytest.fixture
def mode():
    from modes.star_system_mode.star_system_mode import StarSystemMode

    pygame.init()
    pygame.display.set_mode((1, 1))
    pygame.font.init()
    flight = StarSystemMode(Player(), "sol")
    flight.sensors.rng = random.Random(5)
    park(flight, (flight.map_center_x, flight.map_center_y + 15000))  # open space, no patrol zone
    return flight


def park(mode, point):
    mode.x_position = int(point[0]) // TILE_SIZE
    mode.y_position = int(point[1]) // TILE_SIZE


def near(mode, dx, dy):
    x, y = mode.ship_center()
    return (x + dx, y + dy)


def raider(mode, dx, dy, kind="raider", sponsor="dominion", **kw):
    ship = Privateer(kind, sponsor, near(mode, dx, dy), mode, rng=random.Random(1), **kw)
    mode.add_vessel(ship)
    return ship


def test_classes_differ_in_speed_and_toughness():
    speeds = [CLASSES[k]["speed"] for k in ("cutter", "raider", "gunship")]
    hulls = [CLASSES[k]["hull"] for k in ("cutter", "raider", "gunship")]
    assert speeds == sorted(speeds, reverse=True) and hulls == sorted(hulls)


def test_boosting_doubles_speed(mode):
    ship = raider(mode, 3000, 0)
    ship.boosting = True
    assert ship.speed == 2 * CLASSES["raider"]["speed"]


def test_unseen_and_unheard_they_patrol(mode):
    ship = raider(mode, 3000, 0)
    start = ship.position
    mode.spend_turns(3)
    assert ship.state == PATROL and ship.position != start


def test_in_sight_they_close_to_weapon_range_shield_up_while_they_can_fire(mode):
    from modes.star_system_mode.combat import charged

    mode.player.ship.shield_up = True  # loud enough to be seen at 700 px
    ship = raider(mode, 700, 0)
    mode.spend_turns(30)
    assert ship.state == ENGAGE and ship.ship.shield_up == charged(ship.ship)
    assert ENGAGE_RANGE - 2 * TILE_SIZE <= math.dist(ship.position, mode.ship_center()) <= ENGAGE_RANGE + TILE_SIZE


def test_a_heard_ping_sends_them_hunting_then_searching_then_home(mode):
    ship = raider(mode, 2500, 0)
    mode.area_ping()
    park(mode, near(mode, 0, -9000))  # slip away, beyond its pings, while it heads for the fix
    mode.spend_turns(1)
    assert ship.state == HUNT
    for _ in range(200):
        mode.spend_turns(1)
        if ship.state != HUNT:
            break
    assert ship.state == SEARCH
    assert math.dist(ship.position, ship.player_fix[0]) <= ARRIVED + TILE_SIZE
    mode.spend_turns(SEARCH_TURNS + 8)
    assert ship.state == PATROL and ship.player_fix is None


def test_assembly_friends_are_searched_for_longer():
    assert search_turns({"assembly": 50}) > search_turns({}) == SEARCH_TURNS


def test_friends_of_the_sponsor_are_waved_by(mode):
    mode.player.reputation["dominion"] = WAVE_BY
    mode.player.ship.shield_up = True
    ship = raider(mode, 400, 0)
    mode.spend_turns(6)
    assert ship.state == PATROL and not ship.ship.shield_up


def test_they_break_off_inside_an_assembly_patrol_zone(mode):
    station = mode.selected_system.objects[0].world_center()
    park(mode, station)
    mode.player.ship.shield_up = True
    ship = raider(mode, 3400, 0)
    ship.state, ship.player_fix = HUNT, (mode.ship_center(), 0)
    mode.spend_turns(2)
    assert ship.state == PATROL and ship.player_fix is None


def test_badly_hurt_they_boost_for_home(mode):
    ship = raider(mode, 300, 0, home=near(mode, 4000, 0))
    ship.ship.hull = ship.ship.max_hull * 0.2
    start = math.dist(ship.position, ship.home)
    mode.spend_turns(2)
    assert ship.state == RETREAT and ship.boosting
    assert math.dist(ship.position, ship.home) < start
    ship.ship.fuel = BOOST_RESERVE
    mode.spend_turns(1)
    assert not ship.boosting


def test_they_never_fly_into_the_glare(mode):
    system = mode.selected_system
    core = (system.map_center_x, system.map_center_y)
    edge = (core[0] + 1100, core[1])  # just outside the heat zone
    ship = Privateer("cutter", "cohort", edge, mode, rng=random.Random(2))
    for _ in range(20):
        ship.step(core)
        assert not mode.sensors.blind(ship.position)


def test_they_never_fly_into_a_patrol_zone(mode):
    station = mode.selected_system.objects[0].world_center()
    from modes.star_system_mode.star_systems import PATROL_RADIUS

    outside = (station[0] + PATROL_RADIUS + 60, station[1])
    ship = Privateer("raider", "dominion", outside, mode, rng=random.Random(3))
    for _ in range(20):
        ship.step(station)
        assert not mode.selected_system.in_patrol_zone(ship.position)


def test_a_seen_privateer_draws_its_faction_sprite(mode):
    mode.player.ship.shield_up = True
    ship = raider(mode, 120, 60, kind="gunship", sponsor="caravaneers")
    ship.ship.shield_up = True
    mode.handle_continuous_updates()
    mode.draw(pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT)))
    assert ship._sprite is not None


def test_the_hud_says_hunted_while_any_privateer_is_after_you(mode):
    ship = raider(mode, 3000, 0)
    assert not mode.hunted()
    ship.state = HUNT
    assert mode.hunted()


def test_a_sponsor_friend_is_told_they_were_recognised(mode):
    mode.player.reputation["cohort"] = WAVE_BY
    ship = raider(mode, 1000, 0, sponsor="cohort")
    mode.vessel_ping(ship)
    mode.spend_turns(1)  # its ping arrives
    assert mode.events.latest() == "PINGED BY COHORT - THEY KNOW YOU"
