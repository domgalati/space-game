from entities.actor import Actor
from entities.npcs.npc import NPC
from entities.npcs.npc_generator import build_npc, roll_npc_record
from entities.player import Player
from world.factions import FACTIONS


def test_players_and_npcs_are_both_actors_with_standing_for_every_faction():
    for actor in (Player(), NPC()):
        assert isinstance(actor, Actor)
        assert set(actor.reputation) == set(FACTIONS)
        assert actor.inventory.capacity and actor.equipment == {}


def test_damage_and_healing_stay_within_health():
    actor = Actor(max_health=30)
    assert actor.take_damage(12) == 12 and actor.health == 18
    assert actor.take_damage(50) == 18 and not actor.alive
    assert actor.take_damage(-5) == 0
    assert actor.heal(100) == 30 and actor.alive


def test_an_npc_takes_its_faction_from_its_record():
    npc = build_npc(roll_npc_record("sol/terramonta/Miner-01", "Miner", "assembly"))
    assert npc.faction == "assembly"


def test_what_every_actor_has_survives_a_player_save():
    player = Player()
    player.max_health, player.health = 120, 80
    player.equipment["hand"] = "sidearm"
    player.stats["strength"] = 14
    loaded = Player.from_dict(player.to_dict())
    assert (loaded.max_health, loaded.health) == (120, 80)
    assert loaded.equipment == {"hand": "sidearm"}
    assert loaded.stats["strength"] == 14
