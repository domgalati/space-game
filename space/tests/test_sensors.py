import math
import random

import pygame
import pytest

from entities.player import Player
from modes.star_system_mode.sensors import (
    PING_RANGE, SIGNATURE_BOOST, SIGNATURE_CARGO, SIGNATURE_CRUISE, SIGNATURE_DARK, SIGNATURE_SHIELD,
    WEDGE_TURNS, bearing, signature,
)
from modes.star_system_mode.star_systems import PATROL_RADIUS
from modes.star_system_mode.vessels import DRONE_PING_EVERY, Drone, Vessel


def test_holding_still_with_the_shield_down_is_running_dark():
    assert signature(moved=False, shield_up=False, boosting=False) == SIGNATURE_DARK
    assert signature(moved=True, shield_up=False, boosting=False) == SIGNATURE_CRUISE
    loudest = signature(moved=True, shield_up=True, boosting=True, cargo_fill=1.0)
    assert loudest == SIGNATURE_CRUISE + SIGNATURE_SHIELD + SIGNATURE_BOOST + SIGNATURE_CARGO


@pytest.fixture
def mode():
    from modes.star_system_mode.star_system_mode import StarSystemMode

    pygame.init()
    pygame.display.set_mode((1, 1))
    pygame.font.init()
    flight = StarSystemMode(Player(), "sol")
    flight.sensors.rng = random.Random(3)
    return flight


def offset(mode, dx, dy):
    x, y = mode.ship_center()
    return (x + dx, y + dy)


class StillDrone(Drone):
    """A drone that never wanders, so distances in a test stay put."""

    def take_turn(self):
        self.turns += 1
        if self.turns % DRONE_PING_EVERY == 0:
            self.mode.vessel_ping(self)


def test_sensing_works_both_ways_by_signature(mode):
    near = Vessel(offset(mode, SIGNATURE_DARK - 10, 0))
    far = Vessel(offset(mode, SIGNATURE_DARK + 10, 0))
    assert mode.sees(near) and not mode.sees(far)
    assert mode.seen_by(near) and not mode.seen_by(far)
    mode.player.ship.shield_up = True
    assert mode.seen_by(far)


def test_nobody_sees_into_or_out_of_the_glare(mode):
    system = mode.selected_system
    core = (system.map_center_x, system.map_center_y)
    beside = Vessel((core[0] + 50, core[1]))
    assert not mode.sensors.sees(core, beside.position, 10_000)
    assert not mode.sensors.sees((core[0] + 3000, core[1]), core, 10_000)


def test_area_ping_finds_hidden_ships_costs_a_turn_and_gives_you_away(mode):
    hidden = StillDrone(offset(mode, 2000, 0), mode)
    beyond = StillDrone(offset(mode, PING_RANGE + 100, 0), mode)
    for drone in (hidden, beyond):
        mode.add_vessel(drone)
    lines = mode.area_ping()
    assert lines[0] == "Area ping: 1 unknown contact."
    assert mode.clock.turn == 1
    assert hidden.player_fix is not None and beyond.player_fix is None
    (wedge,) = mode.sensors.wedges
    true_bearing = bearing(wedge.origin, hidden.position)
    assert abs(wedge.angle - true_bearing) <= wedge.half_width
    assert not wedge.hostile


def test_area_ping_is_refused_in_the_glare(mode):
    system = mode.selected_system
    mode.x_position = system.map_center_x // 24
    mode.y_position = system.map_center_y // 24
    assert "Glare" in mode.area_ping()[0]
    assert mode.clock.turn == 0


def test_an_enemy_ping_points_back_at_once_and_catches_you_when_it_arrives(mode):
    drone = StillDrone(offset(mode, -2000, 1000), mode)  # about 2240 m: three turns out
    mode.add_vessel(drone)
    mode.spend_turns(DRONE_PING_EVERY)
    (wedge,) = mode.sensors.wedges
    assert wedge.hostile
    assert abs(wedge.angle - bearing(mode.ship_center(), drone.position)) <= wedge.half_width
    assert drone.player_fix is None and "INCOMING PING" in mode.ping_warning()
    mode.spend_turns(3)
    assert drone.player_fix is not None
    assert "HAS YOUR POSITION" in mode.notice[0]

def test_wedges_fade_over_a_few_turns(mode):
    mode.add_vessel(Vessel(offset(mode, 2000, 0)))
    mode.area_ping()  # the ping itself is the first turn
    mode.spend_turns(WEDGE_TURNS - 2)
    mode.sensors.prune(mode.clock.now, 0)
    assert mode.sensors.wedges
    mode.spend_turns(1)
    mode.sensors.prune(mode.clock.now, 0)
    assert not mode.sensors.wedges


def test_moving_is_louder_than_waiting(mode):
    mode.last_action = "wait"
    quiet = mode.player_signature()
    mode.last_action = "move"
    assert mode.player_signature() > quiet == SIGNATURE_DARK


def test_patrol_zones_cover_assembly_worlds_and_the_station(mode):
    system = mode.selected_system
    by_name = {p.name: p for p in system.planets}
    terramonta, ferrica = by_name["Terramonta"].position, by_name["Ferrica"].position
    assert system.in_patrol_zone((terramonta[0] + PATROL_RADIUS - 10, terramonta[1]))
    assert not system.in_patrol_zone(ferrica)
    assert system.in_patrol_zone(system.objects[0].world_center())


def test_ping_with_no_name_from_the_terminal_is_an_area_ping(mode):
    assert mode.ping("")[0].startswith("Area ping")


def test_test_drones_spawn_near_the_ship_and_wander(mode):
    mode.spawn_test_drones(3)
    assert len(mode.vessels) == 3
    start = [v.position for v in mode.vessels]
    assert all(900 <= math.dist(p, mode.ship_center()) <= 3500 for p in start)
    mode.spend_turns(DRONE_PING_EVERY - 1)
    assert [v.position for v in mode.vessels] != start


def test_running_dark_dodges_a_distant_ping_and_says_so(mode):
    drone = StillDrone(offset(mode, 4000, 0), mode)
    mode.add_vessel(drone)
    mode.last_action = "wait"
    mode.spend_turns(DRONE_PING_EVERY)
    assert "DODGE: HOLD STILL, SHIELD DOWN" in mode.ping_warning()
    mode.spend_turns(4)
    assert drone.player_fix is None and mode.notice[0] == "PING MISSED YOU"

def test_making_noise_gets_you_caught_at_long_range(mode):
    drone = StillDrone(offset(mode, 4000, 0), mode)
    mode.add_vessel(drone)
    mode.player.ship.shield_up = True
    mode.spend_turns(DRONE_PING_EVERY + 4)
    assert drone.player_fix is not None

def test_your_ping_only_finds_dark_ships_within_half_range(mode):
    dark = Vessel(offset(mode, 4000, 0))
    loud = Vessel(offset(mode, 0, 4000))
    loud.moved = True
    for vessel in (dark, loud):
        mode.add_vessel(vessel)
    assert mode.area_ping()[0] == "Area ping: 1 unknown contact."
    assert dark.player_fix is not None  # it still heard you


def test_the_catch_range_slides_from_dark_to_loud():
    from modes.star_system_mode.sensors import LOUD_AT, PING_DARK_RANGE, catch_range, loudest_unfound

    assert catch_range(SIGNATURE_DARK) == PING_DARK_RANGE
    assert PING_DARK_RANGE < catch_range(SIGNATURE_CRUISE) < PING_RANGE
    assert catch_range(LOUD_AT) == catch_range(LOUD_AT * 2) == PING_RANGE
    assert loudest_unfound(PING_DARK_RANGE) is None
    assert catch_range(loudest_unfound(4500)) == pytest.approx(4500)


def test_a_ping_too_close_cannot_be_dodged(mode):
    drone = StillDrone(offset(mode, 2000, 0), mode)
    mode.add_vessel(drone)
    mode.spend_turns(DRONE_PING_EVERY)
    assert mode.ping_warning().endswith("TOO CLOSE TO DODGE")


def test_your_ping_reports_rough_ranges(mode):
    mode.add_vessel(Vessel(offset(mode, 1234, 0)))
    lines = mode.area_ping()
    assert "Contact E, about 1200 m" in lines[1]
    assert mode.sensors.wedges[0].distance == pytest.approx(1234)
