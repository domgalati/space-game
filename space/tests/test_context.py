import random
from types import SimpleNamespace

import pytest

from dialogue import DialogueRunner, parse_yarn
from dialogue.context import GameContext
from dialogue.errors import DialogueError
from entities.npcs.npc import NPC
from entities.player import Player
from fakes import run_until_input


def make_npc():
    npc = NPC()
    npc.firstname = "Sue"
    npc.lastname = "Reyes"
    npc.job_title = "Miner"
    npc.guild = "assembly"
    npc.hobbies = ["Chess", "Stargazing", "Baking"]
    npc.species = "vessari"
    return npc


def make_context(player=None):
    npc_state = {"mood": 0, "vars": {}, "visited": {}}
    world = SimpleNamespace(globals={})
    player = player or Player()
    ctx = GameContext(make_npc(), npc_state, player, world, location="Terramonta", rng=random.Random(1))
    return ctx, npc_state, world, player


def run(ctx, body):
    program = parse_yarn(f"title: Start\n---\n{body}\n===\n", "ctx.yarn")
    runner = DialogueRunner(program, ctx)
    runner.start()
    return run_until_input(runner)


def test_this_vars_are_per_npc_and_others_global():
    ctx, npc_state, world, _ = make_context()
    run(ctx, "<<set $this_met to true>>\n<<set $quest_stage to 2>>")
    assert npc_state["vars"] == {"this_met": True}
    assert world.globals == {"quest_stage": 2}


def test_inventory_currency_and_reputation_commands():
    player = Player()
    player.currency = 30
    ctx, _, _, player = make_context(player)
    run(
        ctx,
        '<<give "Rations" 3>>\n<<take "Rations" 1>>\n<<pay 20>>\n<<charge 100>>\n<<rep Assembly 5>>',
    )
    assert player.inventory.items == {"Rations": 2}
    assert player.currency == 0
    assert player.reputation["assembly"] == 5
    assert ctx.changes == [
        "Received 3 Rations.",
        "Handed over 1 Rations.",
        "Received $20.",
        "Paid $50.",
        "Assembly reputation +5.",
    ]


def test_mood_is_clamped_and_not_a_summary_change():
    ctx, npc_state, _, _ = make_context()
    run(ctx, "<<mood 150>>")
    assert npc_state["mood"] == 100
    run(ctx, "<<mood -500>>")
    assert npc_state["mood"] == -100
    assert ctx.changes == []


def test_functions():
    ctx, npc_state, _, player = make_context()
    player.inventory.add_item("Steel", 4)
    npc_state["mood"] = 25
    events = run(
        ctx,
        '{npc_name()} {npc_job()} {npc_guild()} {npc_species()}\n'
        '{has_item("Steel", 4)} {has_item("Steel", 5)} {item_count("Steel")}\n'
        '{mood()} {disposition()} {npc_has_hobby("chess")} {npc_has_hobby("Golf")}\n'
        '{rep("assembly")} {currency()} {location()}',
    )
    assert [e.text for e in events[:-1]] == [
        "Sue Reyes Miner assembly Vessari",
        "true false 4",
        "25 Friendly true false",
        "0 0 Terramonta",
    ]


def test_job_line_uses_goal_activity():
    ctx, _, _, _ = make_context()
    (line, _end) = run(ctx, "{job_line()}")
    assert line.text.endswith("Right now I'm just stretching my legs.")


def test_goods_opinion_falls_back_without_economy():
    ctx, _, _, _ = make_context()
    (line, _end) = run(ctx, "{goods_opinion()}")
    assert line.text == "Can't complain. Can't afford to."


def test_goods_opinion_reads_economy():
    ctx, _, _, _ = make_context()
    ctx.economy = SimpleNamespace(
        place="Terramonta",
        data={"Terramonta": {"goods": {"Steel": {"basePrice": 100, "currentPrice": 150}}}},
    )
    from dialogue import topics

    line = topics.goods_opinion(ctx.npc, ctx.economy, random.Random(0))
    assert "Steel" in line


def test_unknown_function_and_command_errors():
    ctx, _, _, _ = make_context()
    with pytest.raises(DialogueError, match="ctx.yarn:3.*Unknown function"):
        run(ctx, "{explode()}")
    with pytest.raises(DialogueError, match="ctx.yarn:3.*Unknown command"):
        run(ctx, "<<explode>>")
