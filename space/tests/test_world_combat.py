from types import SimpleNamespace

from entities.player import Player
from world.combat import kill, loot_goods
from world.factions import KILL_LAW_STANDING, KILL_SPONSOR_STANDING
from world.world_state import WorldState


def body(place, faction):
    return SimpleNamespace(id=place, planet_guild=faction)


def test_a_kill_anywhere_logs_moves_standing_and_is_announced():
    player, world = Player(), WorldState()
    heard = []
    world.events.on("killed", heard.append)
    summary = kill(player, world, "cohort", "brawler", law="assembly", place="sol/arboresia")
    assert player.kill_log == [{"sponsor": "cohort", "kind": "brawler"}]
    assert player.reputation["cohort"] == KILL_SPONSOR_STANDING
    assert player.reputation["assembly"] == KILL_LAW_STANDING
    assert summary == f"COHORT {KILL_SPONSOR_STANDING:+d}, ASSEMBLY {KILL_LAW_STANDING:+d}"
    assert heard[0].details == {"faction": "cohort", "kind": "brawler", "place": "sol/arboresia"}


def test_loot_comes_from_the_factions_own_markets():
    markets = {"a/home": {"goods": {"steel": {}}}, "a/other": {"goods": {"rations": {}}}}
    bodies = [body("a/home", "dominion"), body("a/other", "cohort")]
    assert loot_goods(markets, bodies, "dominion") == {"steel"}


def test_without_markets_of_its_own_a_fighter_carries_anything_on_sale():
    markets = {"a/other": {"goods": {"rations": {}, "steel": {}}}}
    assert loot_goods(markets, [body("a/home", "dominion")], "dominion") == {"rations", "steel"}
