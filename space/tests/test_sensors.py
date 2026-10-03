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


def test_an_enemy_ping_points_back_at_it_and_fixes_your_position(mode):
    drone = StillDrone(offset(mode, -3000, 1000), mode)
    mode.add_vessel(drone)
    mode.spend_turns(DRONE_PING_EVERY)
    assert drone.player_fix is not None
    (wedge,) = mode.sensors.wedges
    assert wedge.hostile
    assert abs(wedge.angle - bearing(mode.ship_center(), drone.position)) <= wedge.half_width
    assert len(mode.sensors.rings) == 1


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
