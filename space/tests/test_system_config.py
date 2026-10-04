import json
import random

import pygame
import pytest

from modes.star_system_mode.star_systems import HEAT_MAX, SUN_RADIUS, StarSystem


@pytest.fixture(scope="module", autouse=True)
def _display():
    pygame.init()
    pygame.display.set_mode((1, 1))


def write_system(tmp_path, **extra):
    """A small system file unlike Sol: its own star and politics, unless `extra` says otherwise."""
    data = {
        "id": "kestrel",
        "name": "Kestrel",
        "seed": 7,
        "planets": [
            {"id": "rook", "name": "Rook", "type": "Industrial", "guild": "dominion",
             "image_path": "space/assets/img/planets/Ice.png"},
            {"id": "wren", "name": "Wren", "type": "Terran", "guild": "cohort",
             "image_path": "space/assets/img/planets/Terran.png"},
        ],
        **extra,
    }
    path = tmp_path / "kestrel.json"
    path.write_text(json.dumps(data))
    return StarSystem(str(path))


def test_a_system_brings_its_own_star(tmp_path):
    system = write_system(tmp_path, star={"radius": 900, "heat_start": 0.8, "heat_max": 20})
    centre = (system.map_center_x, system.map_center_y)
    assert system.heat_at(centre) == 20
    assert system.heat_at((centre[0] + 900 * 0.79, centre[1])) > 0
    assert system.heat_at((centre[0] + 900 * 0.8, centre[1])) == 0


def test_a_system_without_star_settings_gets_sols_star(tmp_path):
    system = write_system(tmp_path)
    assert system.star_radius == SUN_RADIUS
    assert system.heat_at((system.map_center_x, system.map_center_y)) == HEAT_MAX


def test_the_law_and_its_patrols_come_from_the_system(tmp_path):
    system = write_system(tmp_path, law="dominion", raiders=["cohort"])
    rook, wren = system.planets
    assert system.politics.law == "dominion"
    assert system.politics.licenses_raiders("cohort")
    assert not system.politics.licenses_raiders("assembly")
    assert system.in_patrol_zone(rook.position)
    assert not system.in_patrol_zone(wren.position)


def test_a_lawless_system_has_no_patrols(tmp_path):
    system = write_system(tmp_path)
    assert system.politics.law is None
    assert system.patrol_zones() == []


def test_loading_a_system_leaves_the_shared_random_alone(tmp_path):
    random.seed(99)
    expected = [random.random() for _ in range(3)]
    random.seed(99)
    write_system(tmp_path)
    assert [random.random() for _ in range(3)] == expected


def test_the_same_seed_lays_a_system_out_the_same_way(tmp_path):
    first = [p.position for p in write_system(tmp_path).planets]
    assert [p.position for p in write_system(tmp_path).planets] == first


def test_bodies_and_ships_say_what_they_are():
    from modes.star_system_mode.privateers import Privateer
    from modes.star_system_mode.vessels import Drone, Vessel

    sol = StarSystem("space/star_systems/sol.json")
    assert {p.category for p in sol.planets} == {"planet"}
    assert {o.category for o in sol.objects} == {"station"}
    assert all(p.world_center() == p.position for p in sol.planets)
    assert Privateer.armed and not Drone.armed and not Vessel.armed
