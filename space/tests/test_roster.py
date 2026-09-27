from entities.npcs.npc_generator import build_npc, roll_npc_record
from world.roster import NPCRoster
from world.world_state import WorldState


def test_same_id_rolls_same_person():
    assert roll_npc_record("Terramonta/Miner-01", "Miner", "assembly") == roll_npc_record(
        "Terramonta/Miner-01", "Miner", "assembly"
    )
    assert roll_npc_record("Terramonta/Miner-01", "Miner", "assembly") != roll_npc_record(
        "Terramonta/Miner-02", "Miner", "assembly"
    )


def test_record_shape_and_hobbies_unique():
    record = roll_npc_record("Terramonta/Foreman-03", "Foreman", "assembly")
    assert record["id"] == "Terramonta/Foreman-03"
    assert record["job"] == "Foreman"
    assert len(set(record["hobbies"])) == 3
    assert record["portrait"]["species"] == record["species"]
    assert record["portrait"]["layers"]["outfit"] == "foreman"


def test_roster_is_stable_across_save_and_load(tmp_path):
    path = tmp_path / "world_state.yaml"
    world = WorldState(str(path))
    first = NPCRoster(world).for_location("Terramonta", {"Miner": 3, "Foreman": 2}, "assembly")
    assert [r["id"] for r in first] == [
        "Terramonta/Miner-01", "Terramonta/Miner-02", "Terramonta/Miner-03",
        "Terramonta/Foreman-01", "Terramonta/Foreman-02",
    ]
    world.npc_state("Terramonta/Miner-01", default_mood=10)["vars"]["this_met"] = True
    world.globals["quest_stage"] = 2
    world.save()

    loaded = WorldState.load(str(path))
    again = NPCRoster(loaded).for_location("Terramonta", {"Miner": 3, "Foreman": 2}, "assembly")
    assert again == first
    assert loaded.npc_state("Terramonta/Miner-01") == {"mood": 10, "vars": {"this_met": True}, "visited": {}}
    assert loaded.globals == {"quest_stage": 2}


def test_headcount_changes_keep_residents_on_file(tmp_path):
    world = WorldState(str(tmp_path / "w.yaml"))
    roster = NPCRoster(world)
    three = roster.for_location("Etheora", {"Miner": 3}, "assembly")
    one = roster.for_location("Etheora", {"Miner": 1}, "assembly")
    assert one == three[:1]
    assert len(world.rosters["Etheora"]) == 3
    four = roster.for_location("Etheora", {"Miner": 4}, "assembly")
    assert four[:3] == three
    assert four[3]["id"] == "Etheora/Miner-04"


def test_build_npc_from_record():
    npc = build_npc(roll_npc_record("Nexum Astra/Security-01", "Security", "assembly"))
    assert type(npc).__name__ == "Security"
    assert npc.npc_id == "Nexum Astra/Security-01"
    assert npc.sprite.endswith("security.png")
    assert npc.portrait_recipe["layers"]["outfit"] == "security"

    unknown = build_npc(dict(roll_npc_record("X/Bartender-01", "Bartender", "assembly"), sprite=None))
    assert type(unknown).__name__ == "NPC"
    assert unknown.sprite.endswith("dockworker.png")
