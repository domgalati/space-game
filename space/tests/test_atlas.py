import os

import pygame
import pytest

from entities.player import Player
from util.economy.economy import load_market_data
from world.atlas import body, place_name, system_of


@pytest.fixture(scope="module")
def sol():
    from modes.star_system_mode.star_systems import StarSystem

    return StarSystem("space/star_systems/sol.json")


def test_bodies_have_system_qualified_ids_and_keep_their_names(sol):
    bodies = [*sol.planets, *sol.objects]
    ids = [b.id for b in bodies]
    assert len(set(ids)) == len(ids)
    assert all(system_of(place) == "sol" for place in ids)
    terramonta = next(b for b in sol.planets if b.name == "Terramonta")
    assert terramonta.id == "sol/terramonta"
    assert body("sol/nexum-astra")["name"] == "Nexum Astra"


def test_place_names_fall_back_to_the_key():
    assert place_name("sol/etheora") == "Etheora"
    assert place_name("Somewhere Else") == "Somewhere Else"


def test_every_market_belongs_to_a_known_body():
    for place in load_market_data():
        assert body(place), f"economy.yaml market {place!r} is not a body id"


def test_landing_maps_come_from_the_system_file(sol):
    by_id = {b.id: b for b in [*sol.planets, *sol.objects]}
    for place in ("sol/terramonta", "sol/etheora", "sol/nexum-astra"):
        assert os.path.exists(by_id[place].map_path)
    assert by_id["sol/ferrica"].map_path is None


@pytest.fixture
def player():
    pygame.init()
    pygame.display.set_mode((1, 1))
    return Player()


def test_the_ship_position_lives_on_the_player(player):
    from modes.star_system_mode.star_system_mode import StarSystemMode

    flight = StarSystemMode(player, "sol")
    assert player.location.system == "sol"
    assert player.location.tile == (flight.x_position, flight.y_position)
    flight.x_position += 5
    assert StarSystemMode(player, "sol").x_position == flight.x_position  # resumes, no respawn


def test_undocking_charts_the_body_by_id_and_clears_it(player):
    from modes.star_system_mode.star_system_mode import StarSystemMode

    flight = StarSystemMode(player, "sol")
    etheora = next(b for b in flight.selected_system.planets if b.id == "sol/etheora")
    player.location.body = etheora.id
    flight.landing_requested = True
    flight.undock(etheora)
    assert player.location.body is None
    assert not flight.landing_requested
    assert "sol/etheora" in player.charted_planets
    assert flight.nav.is_charted(etheora)
