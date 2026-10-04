import pygame
import pytest
import yaml

from entities.player import Player
from util.economy import trade
from util.economy.economy import Economy
from world.events import ANY, Events
from world.save import SaveError, load_game, save_game
from world.world_state import WorldState


@pytest.fixture(scope="module", autouse=True)
def _display():
    pygame.init()
    pygame.display.set_mode((1, 1))


def recorder(events, name=ANY):
    heard = []
    events.on(name, heard.append)
    return heard


def test_listeners_hear_their_event_and_can_unsubscribe():
    events = Events()
    docked, everything = recorder(events, "docked"), recorder(events)
    stop = events.on("docked", lambda event: stop())  # unsubscribing mid-emit is safe
    events.emit("docked", body="sol/terramonta")
    events.emit("sold", good="Steel")
    assert [e.details for e in docked] == [{"body": "sol/terramonta"}]
    assert [e.name for e in everything] == ["docked", "sold"]


def test_trades_are_announced_with_the_place():
    world = WorldState()
    heard = recorder(world.events)
    data = {"sol/terramonta": {"goods": {"Steel": {"basePrice": 100, "currentPrice": 100}}}}
    economy = Economy("sol/terramonta", data, events=world.events)
    player = Player()
    player.currency = 1000
    trade.handle("buy", "3 steel", player, economy)
    trade.handle("sell", "1 steel", player, economy)
    assert [(e.name, e.details["good"], e.details["quantity"], e.details["place"]) for e in heard] == [
        ("bought", "Steel", 3, "sol/terramonta"), ("sold", "Steel", 1, "sol/terramonta"),
    ]
    assert heard[0].details["credits"] == 1000 - player.currency + heard[1].details["credits"]


def test_dialogue_announces_the_talk_and_its_story_beats():
    from dialogue.conversation import Conversation
    from entities.npcs.npc import NPC

    world = WorldState()
    heard = recorder(world.events)
    npc = NPC()
    npc.npc_id, npc.firstname, npc.lastname = "sol/terramonta/Foreman-01", "Ada", "Vance"
    conversation = Conversation(npc, Player(), world)
    conversation.context.run_command("event", ["met_the_foreman"])
    assert [(e.name, e.details) for e in heard] == [
        ("talked", {"npc": "sol/terramonta/Foreman-01"}),
        ("met_the_foreman", {"npc": "sol/terramonta/Foreman-01"}),
    ]


def test_a_destroyed_privateer_is_announced():
    from modes.star_system_mode.star_system_mode import StarSystemMode

    world = WorldState()
    flight = StarSystemMode(Player(), "sol", world)
    flight.spawn_test_privateers(1)
    heard = recorder(world.events, "privateer_destroyed")
    privateer = flight.vessels[0]
    flight.destroy(privateer)
    assert heard[0].details == {"sponsor": privateer.sponsor, "kind": privateer.kind, "system": "sol"}


def test_a_run_survives_save_and_load(tmp_path):
    player, world = Player(), WorldState()
    player.currency = 4321
    player.reputation["dominion"] = -12
    player.charted_planets.add("sol/etheora")
    player.ship.hull = 55.5
    player.ship.shield_up = True
    player.ship.cargo.add_item("Steel", 7)
    player.inventory.add_item("Keycard", 1)
    player.kill_log.append({"sponsor": "cohort", "kind": "raider"})
    player.location.system, player.location.tile = "sol", (1800, 1750)
    world.globals["quest_stage"] = 2
    world.npc_state("sol/terramonta/Miner-01", 10)["vars"]["this_met"] = True
    world.markets_data()["sol/terramonta"]["goods"]["steel"]["currentPrice"] = 321.5

    path = save_game(player, world, str(tmp_path / "save.yaml"))
    loaded_player, loaded_world = load_game(path)

    assert loaded_player.to_dict() == player.to_dict()
    assert loaded_player.location.tile == (1800, 1750)
    assert loaded_world.globals == {"quest_stage": 2}
    assert loaded_world.npc_state("sol/terramonta/Miner-01")["vars"] == {"this_met": True}
    assert loaded_world.markets_data()["sol/terramonta"]["goods"]["steel"]["currentPrice"] == 321.5


def test_a_new_players_fields_survive_an_older_save_that_lacks_them():
    player = Player.from_dict({"currency": 50, "reputation": {"cohort": 5}})
    assert player.currency == 50
    assert player.reputation["cohort"] == 5 and player.reputation["assembly"] == 0
    assert player.ship.hull == player.ship.max_hull


def test_unreadable_saves_say_why(tmp_path):
    with pytest.raises(SaveError, match="Can't read"):
        load_game(str(tmp_path / "missing.yaml"))
    old = tmp_path / "old.yaml"
    old.write_text(yaml.safe_dump({"version": 0}))
    with pytest.raises(SaveError, match="version 0"):
        load_game(str(old))


def test_docking_announces_itself_and_autosaves(tmp_path):
    from game import Game
    from modes.transitions import Land

    game = Game(Player(), WorldState(), "sol")
    game.save_to = str(tmp_path / "save.yaml")
    heard = recorder(game.events)
    terramonta = game.mode.selected_system.body("sol/terramonta")
    game.land(Land(terramonta))
    assert [(e.name, e.details) for e in heard] == [("docked", {"body": "sol/terramonta", "system": "sol"})]
    assert load_game(game.save_to)[0].location.body == "sol/terramonta"


def test_a_save_made_ashore_loads_ashore(tmp_path):
    from game import Game
    from modes.planetary_mode.planetary_mode import PlanetaryMode
    from modes.star_system_mode.star_system_mode import StarSystemMode

    player = Player()
    player.location.system, player.location.body = "sol", "sol/etheora"
    path = save_game(player, WorldState(), str(tmp_path / "save.yaml"))
    game = Game.load(path)
    assert isinstance(game.mode, PlanetaryMode) and game.mode.planet.id == "sol/etheora"
    game.mode.return_to_star_system_mode()
    game.update([], 1 / 60)
    assert isinstance(game.mode, StarSystemMode)
    assert game.save_to == path
