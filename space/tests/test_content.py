import xml.etree.ElementTree as ET

from dialogue.conversation import GENERIC_DIALOGUE, Conversation, load_program
from dialogue.runner import End, Line, Options
from entities.npcs.npc_generator import build_npc, roll_npc_record
from entities.player import Player
from util.config import resolve_game_path
from world.characters import character_record, load_character
from world.world_state import WorldState


def talk(conversation, event=None):
    """Lines up to the next menu; returns (lines, options event or End)."""
    event = event or conversation.start()
    lines = []
    while isinstance(event, Line):
        lines.append(event.text)
        event = conversation.advance()
    return lines, event


def choose(conversation, options, text):
    return talk(conversation, conversation.choose(options.choices.index(text)))


def hesk(player=None):
    npc = build_npc(character_record(load_character("hesk_durran")))
    world = WorldState()
    return Conversation(npc, player or Player(), world, location="Terramonta"), npc, world


def test_hesk_definition_builds_an_npc():
    npc = build_npc(character_record(load_character("hesk_durran")))
    assert type(npc).__name__ == "Foreman"
    assert npc.npc_id == "character:hesk_durran"
    assert npc.species == "muroth"
    assert npc.portrait_recipe["layers"]["accessory"] == "goggles"
    assert npc.portrait_recipe["layers"]["back_hair"] is None
    assert npc.sprite == "space/assets/img/npcs/characters/hesk_durran.png"
    load_program(npc.dialogue_file)


def test_hesk_quest_flow():
    player = Player()
    conversation, _, world = hesk(player)
    lines, menu = talk(conversation)
    assert lines[0].startswith("New face.")
    assert "About that ore order." not in menu.choices

    lines, deal = choose(conversation, menu, "Need a hand with anything?")
    lines, menu = choose(conversation, deal, "Deal.")
    assert player.inventory.items == {"mining-permit": 1}
    assert player.reputation["assembly"] == 2
    assert "Need a hand with anything?" not in menu.choices

    lines, menu = choose(conversation, menu, "About that ore order.")
    assert lines == ["I count 0 Raw Minerals. I asked for 5."]

    player.inventory.add_item("raw-minerals", 6)
    lines, menu = choose(conversation, menu, "About that ore order.")
    assert player.currency == 650
    assert player.inventory.items["raw-minerals"] == 1
    assert world.globals["terramonta_ore_delivered"] is True
    assert "About that ore order." not in menu.choices
    assert conversation.disposition == "Friendly"
    assert conversation.summary_lines() == [
        "Spoke with Hesk Durran. Hesk seems Friendly.",
        "Received 1 Mining Permit.",
        "Assembly reputation +2.",
        "Handed over 5 Raw Minerals.",
        "Received $650.",
        "Assembly reputation +5.",
    ]


def test_hesk_tusks_node_blocks_leaving():
    conversation, _, _ = hesk()
    _, menu = talk(conversation)
    _, reply = choose(conversation, menu, "Nice tusks.")
    assert not conversation.can_exit
    _, menu = choose(conversation, reply, "You heard me.")
    assert conversation.can_exit
    assert conversation.disposition == "Wary"
    assert "Nice tusks." not in menu.choices


def test_generic_dialogue_every_topic():
    npc = build_npc(roll_npc_record("Terramonta/Miner-01", "Miner", "assembly"))
    world = WorldState()
    conversation = Conversation(npc, Player(), world, location="Terramonta")
    assert npc.dialogue_file is None
    lines, menu = talk(conversation)
    assert len(lines) == 1
    for topic in ("What do you do here?", "How's business?", "Heard anything interesting?"):
        lines, menu = choose(conversation, menu, topic)
        assert len(lines) == 1 and lines[0]
        assert isinstance(menu, Options)
    lines, end = choose(conversation, menu, "Goodbye.")
    assert isinstance(end, End)
    assert world.npc_state(npc.npc_id)["vars"]["this_met"] is True
    assert world.npc_state(npc.npc_id)["mood"] == 3
    load_program(GENERIC_DIALOGUE)


def test_terramonta_places_hesk():
    tree = ET.parse(resolve_game_path("space/assets/maps/Terramonta.tmx"))
    posts = [g for g in tree.getroot().iter("objectgroup") if g.get("name") == "NPC Posts"]
    assert [o.get("name") for o in posts[0].iter("object")] == ["character:hesk_durran"]
