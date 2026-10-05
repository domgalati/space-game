from types import SimpleNamespace

import pygame
import pytest

from util.config import resolve_game_path


@pytest.fixture(scope="module", autouse=True)
def _display():
    pygame.init()
    pygame.display.set_mode((1, 1))


@pytest.fixture
def ground():
    from modes.planetary_mode.ground_map import GroundMap

    return GroundMap.load(resolve_game_path("space/assets/maps/Nexum Astra.tmx"))


def someone():
    return SimpleNamespace(position=None)


def test_the_map_answers_in_tiles(ground):
    spawn = ground.spawn()
    assert ground.walkable(spawn) and ground.in_bounds(spawn)
    assert not ground.walkable((-1, 0)) and not ground.walkable((ground.width, 0))
    terminal = next(obj for obj in ground.objects if obj.name == "Docking Terminal")
    assert ground.object_at(terminal.tile).name == "Docking Terminal"
    assert terminal.tile in ground.object_tiles(["Docking Terminal"])
    assert ground.markers("NPC Posts")  # this generated map posts its crew
    assert ground.reachable_from(spawn) == set(ground.walkable_tiles())  # one connected floor


def test_one_person_per_tile(ground):
    spawn = ground.spawn()
    first, second = someone(), someone()
    ground.place(first, spawn)
    assert first.position == spawn and ground.occupant(spawn) is first and not ground.free(spawn)
    with pytest.raises(ValueError):
        ground.place(second, spawn)
    beside = next(t for t in ground.neighbours(spawn) if ground.free(t))
    ground.place(second, beside)
    assert not ground.move(first, beside)  # taken
    ground.swap(first, second)
    assert (first.position, second.position) == (beside, spawn)
    assert ground.occupant(beside) is first and ground.occupant(spawn) is second
    ground.remove(first)
    assert first.position is None and ground.free(beside)


def test_walking_into_someone_trades_places_with_them():
    from entities.npcs.npc import NPC
    from entities.player import Player
    from modes.planetary_mode.planetary_mode import PlanetaryMode
    from modes.star_system_mode.star_systems import StarSystem
    from world.world_state import WorldState

    station = StarSystem("space/star_systems/sol.json").body("sol/nexum-astra")
    ashore = PlanetaryMode(station, Player(), WorldState())
    ground, start = ashore.ground, ashore.player_tile
    step = next((dx, dy) for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))
                if ground.free((start[0] + dx, start[1] + dy)))
    target = (start[0] + step[0], start[1] + step[1])
    crew = NPC()
    ground.place(crew, target)
    assert ashore._try_move(*step)
    assert ashore.player_tile == target and crew.position == start
