import pygame
import pytest

from dialogue import conversation as conversation_module
from dialogue.conversation import Conversation
from dialogue.runner import End, Line
from entities.npcs.npc_generator import build_npc, roll_npc_record
from entities.player import Player
from modes.planetary_mode.dialogue_panel import SKINS, DialoguePanel
from world.world_state import WorldState

SCRIPT = """
title: Start
---
Sue: Hello there.
Sue: Second line.
-> Leave
    Sue: Bye.
-> Stay
    <<jump Locked>>
===

title: Locked
tags: noexit
---
Sue: You're not going anywhere.
-> Fine.
    <<stop>>
===
"""


@pytest.fixture(scope="module", autouse=True)
def display():
    pygame.init()
    pygame.display.set_mode((1080, 720))
    yield


@pytest.fixture
def panel(tmp_path):
    script = tmp_path / "test.yarn"
    script.write_text(SCRIPT, encoding="utf-8")
    npc = build_npc(roll_npc_record("T/Miner-01", "Miner", "assembly"))
    npc.dialogue_file = str(script)
    conversation = Conversation(npc, Player(), WorldState(str(tmp_path / "w.yaml")))
    return DialoguePanel(conversation, (880, 520))


def press(panel, key):
    panel.handle_event(pygame.event.Event(pygame.KEYDOWN, key=key, unicode="", mod=0, scancode=0))


def test_typewriter_skip_then_continue_to_options(panel):
    assert panel.line.text == "Hello there."
    assert panel.typing
    press(panel, pygame.K_x)
    assert not panel.typing
    assert isinstance(panel.pending, Line)
    press(panel, pygame.K_RETURN)
    assert panel.line.text == "Second line."
    panel.update(10)
    assert panel.options == ["Leave", "Stay"]


def test_choose_by_number_and_end(panel):
    panel.update(10)
    press(panel, pygame.K_RETURN)
    panel.update(10)
    press(panel, pygame.K_1)
    assert panel.last_choice == "Leave"
    assert panel.line.text == "Bye."
    panel.update(10)
    assert isinstance(panel.pending, End)
    press(panel, pygame.K_RETURN)
    assert panel.closed


def test_noexit_blocks_escape_until_finished(panel):
    panel.update(10)
    press(panel, pygame.K_RETURN)
    panel.update(10)
    press(panel, pygame.K_DOWN)
    press(panel, pygame.K_RETURN)
    assert panel.line.text == "You're not going anywhere."
    panel.update(10)
    press(panel, pygame.K_ESCAPE)
    assert not panel.closed
    assert panel.notice
    press(panel, pygame.K_1)
    assert panel.closed


def test_draw_both_skins(panel):
    screen = pygame.Surface((880, 520))
    panel.draw(screen)
    panel.skin = SKINS["comm"]
    panel.draw(screen)


def test_script_errors_end_the_conversation(tmp_path):
    script = tmp_path / "broken.yarn"
    script.write_text("title: Start\n---\n<<explode>>\n===\n", encoding="utf-8")
    npc = build_npc(roll_npc_record("T/Miner-02", "Miner", "assembly"))
    npc.dialogue_file = str(script)
    conversation = Conversation(npc, Player(), WorldState(str(tmp_path / "w.yaml")))
    panel = DialoguePanel(conversation, (880, 520))
    assert panel.closed
    assert "Unknown command" in conversation.summary_lines()[-1]


def test_generic_dialogue_loads():
    program = conversation_module.load_program(conversation_module.GENERIC_DIALOGUE)
    assert {"Start", "Menu", "Job", "Business", "Rumors", "Goodbye"} <= set(program.nodes)
