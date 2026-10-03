import math
from types import SimpleNamespace

import pygame
import pytest

from modes.star_system_mode.nav_charts import STRONG_SIGNAL_PX, NavCharts
from modes.star_system_mode.star_systems import SUN_RADIUS, StarSystem
from util.config import SCREEN_HEIGHT


@pytest.fixture(scope="module")
def sol():
    return StarSystem("space/star_systems/sol.json")


def opaque_rect(obj):
    """World rect around the station's visible art, not its transparent margins."""
    rect = obj.image.get_bounding_rect()
    return rect.move(obj.position)


def distance_to_rect(point, rect):
    dx = max(rect.left - point[0], 0, point[0] - rect.right)
    dy = max(rect.top - point[1], 0, point[1] - rect.bottom)
    return math.hypot(dx, dy)


def sun_center(system):
    return (system.map_center_x, system.map_center_y)


def test_planets_are_flight_size(sol):
    for planet in sol.planets:
        assert planet.image.get_size() == (2304, 2304)
        assert planet.radius == pytest.approx(1072)


def test_sun_matches_its_art(sol):
    assert sol.sun_image.get_width() > 2 * SUN_RADIUS


def test_station_is_planet_sized_and_clear_of_the_sun(sol):
    (station,) = sol.objects
    assert station.image.get_size() == (2304, 2304)
    assert distance_to_rect(sun_center(sol), opaque_rect(station)) > SUN_RADIUS + 200


def test_bodies_never_overlap(sol):
    sun = sun_center(sol)
    station = opaque_rect(sol.objects[0])
    for planet in sol.planets:
        assert math.dist(planet.position, sun) > planet.radius + SUN_RADIUS
        assert distance_to_rect(planet.position, station) > planet.radius
    for a in sol.planets:
        for b in sol.planets:
            if a is not b:
                assert math.dist(a.position, b.position) > a.radius + b.radius


def test_new_run_starts_in_open_space_under_the_bay(sol):
    (station,) = sol.objects
    spawn = sol.spawn_point()
    local = (int(spawn[0] - station.position[0]), int(spawn[1] - station.position[1]))
    assert station.image.get_at(local).a == 0
    assert math.dist(spawn, sun_center(sol)) > SUN_RADIUS
    assert not any(planet.contains(spawn) for planet in sol.planets)
    ship = pygame.Rect(0, 0, 24, 24)
    ship.center = spawn
    assert not any(ship.colliderect(r) for r in station.approach_rects())
    (bay,) = station.access_points()
    assert 0 < spawn[1] - bay[1] < SCREEN_HEIGHT / 2


def test_atmosphere_is_the_disk_not_the_image(sol):
    planet = sol.planets[0]
    rect = planet.get_rect()
    assert planet.contains(planet.position)
    assert not planet.contains((rect.left + 40, rect.top + 40))


def _planet(radius=1072):
    return SimpleNamespace(name="Far", position=(50000, 40000), orbit_radius=9000, radius=radius)


def test_strong_signal_counts_from_the_rim():
    planet = _planet()
    nav = NavCharts((43000, 43000), set())
    near = (planet.position[0] + planet.radius + STRONG_SIGNAL_PX - 50, planet.position[1])
    lines = nav.ping(planet, near)
    assert nav.is_charted(planet)
    assert any("Strong signal" in line for line in lines)


def test_station_strong_signal_needs_the_bay():
    station = SimpleNamespace(name="Dock", access_points=lambda: [(1000, 1000)])
    nav = NavCharts((0, 0), set())
    assert any("Bay is in range" in line for line in nav.ping_fixed(station, (1000, 1400), (900, 900)))
    far = nav.ping_fixed(station, (1000 + STRONG_SIGNAL_PX + 100, 1000), (900, 900))
    assert not any("Bay is in range" in line for line in far)
