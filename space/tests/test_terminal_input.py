import pygame
import pytest

from modes.planetary_mode.terminal import Pager, Terminal
from modes.star_system_mode.scan_terminal import ScanTerminal


class _Economy:
    def __init__(self, names):
        self._goods = {name: {} for name in names}

    def goods(self):
        return self._goods


class _Planet:
    def __init__(self, name):
        self.name = name


@pytest.fixture(scope="module", autouse=True)
def pygame_ready():
    pygame.init()
    yield


def press(terminal, key, character=""):
    terminal.process_input(pygame.event.Event(pygame.KEYDOWN, key=key, unicode=character, mod=0, scancode=0))


def type_text(terminal, text):
    for character in text:
        if character == " ":
            key = pygame.K_SPACE
        elif character.isdigit():
            key = getattr(pygame, f"K_{character}")
        else:
            key = getattr(pygame, f"K_{character.lower()}")
        press(terminal, key, character)


def docking_terminal(names):
    terminal = Terminal("docking", type("Mode", (), {"economy": _Economy(names)})(), "here")
    terminal.active = True
    terminal.execute_command = lambda command: None
    return terminal


def scan_terminal():
    terminal = ScanTerminal.__new__(ScanTerminal)
    Terminal.__init__(terminal, "scan", None, None)
    terminal.active = True
    terminal.star_system_mode = type("Mode", (), {})()
    terminal.star_system_mode.selected_system = type("System", (), {})()
    terminal.star_system_mode.selected_system.planets = [
        _Planet("Terramonta"),
        _Planet("Governus Centralis"),
        _Planet("Etheora"),
    ]
    return terminal


def test_history_recalls_older_commands_and_restores_the_draft():
    terminal = docking_terminal(["Steel"])
    type_text(terminal, "help")
    press(terminal, pygame.K_RETURN)
    type_text(terminal, "info")
    press(terminal, pygame.K_RETURN)
    type_text(terminal, "buy")

    press(terminal, pygame.K_UP)
    assert terminal.input_buffer == "info"
    press(terminal, pygame.K_UP)
    assert terminal.input_buffer == "help"
    press(terminal, pygame.K_UP)
    assert terminal.input_buffer == "help"

    press(terminal, pygame.K_DOWN)
    assert terminal.input_buffer == "info"
    press(terminal, pygame.K_DOWN)
    assert terminal.input_buffer == "buy"
    press(terminal, pygame.K_DOWN)
    assert terminal.input_buffer == "buy"


def test_history_skips_empty_and_repeated_commands():
    terminal = docking_terminal(["Steel"])
    press(terminal, pygame.K_RETURN)
    type_text(terminal, "help")
    press(terminal, pygame.K_RETURN)
    type_text(terminal, "help")
    press(terminal, pygame.K_RETURN)
    assert terminal.history == ["help"]


def test_unique_command_completion_and_listing_when_ambiguous():
    terminal = docking_terminal(["Steel"])
    type_text(terminal, "dep")
    press(terminal, pygame.K_TAB)
    assert terminal.input_buffer == "depart "

    terminal.input_buffer = ""
    press(terminal, pygame.K_TAB)
    listed = " ".join(terminal.output_buffer)
    assert "depart" in listed
    assert "refuel" in listed
    assert "long" not in listed.split()


def test_buy_completes_a_multiword_good_after_a_quantity():
    terminal = docking_terminal(["Fuel Cells", "Fuel Rods", "Steel", "Stone"])
    type_text(terminal, "buy 5 fu")
    press(terminal, pygame.K_TAB)
    assert terminal.input_buffer == "buy 5 Fuel "
    press(terminal, pygame.K_c, "c")
    press(terminal, pygame.K_TAB)
    assert terminal.input_buffer == "buy 5 Fuel Cells "

    terminal.input_buffer = "buy s"
    terminal.output_buffer.clear()
    press(terminal, pygame.K_TAB)
    assert terminal.input_buffer == "buy St"
    press(terminal, pygame.K_TAB)
    listed = " ".join(terminal.output_buffer)
    assert "Steel" in listed
    assert "Stone" in listed
    assert "Fuel Cells" not in listed


def test_ping_completes_planet_names():
    terminal = scan_terminal()
    type_text(terminal, "ping gov")
    press(terminal, pygame.K_TAB)
    assert terminal.input_buffer == "ping Governus Centralis "

    terminal.input_buffer = "ping "
    terminal.output_buffer.clear()
    press(terminal, pygame.K_TAB)
    listed = " ".join(terminal.output_buffer)
    assert "Terramonta" in listed
    assert "Etheora" in listed
    assert "Governus Centralis" in listed


def printing_terminal(count):
    terminal = Terminal("market", None, "here")
    terminal.active = True

    def run(command):
        terminal.output_buffer.append(f"> {command}")
        terminal.show("\n".join(f"line {i}" for i in range(count)))

    terminal.execute_command = run
    return terminal


def on_screen(terminal):
    rows = terminal.flatten_output_buffer()
    start = max(0, len(rows) - terminal.max_lines - terminal.scroll_position)
    return rows[start:start + terminal.max_lines]


def test_output_that_fits_skips_the_pager():
    terminal = printing_terminal(13)
    press(terminal, pygame.K_RETURN)
    assert terminal.pager is None
    assert len(terminal.output_buffer) == 14


def test_tall_output_opens_the_pager_at_the_top():
    terminal = printing_terminal(40)
    type_text(terminal, "news")
    press(terminal, pygame.K_RETURN)
    assert terminal.output_buffer == ["> news"]
    assert terminal.pager.visible()[0] == "line 0"
    assert len(terminal.pager.visible()) == terminal.max_lines


def test_pager_keys_move_by_page_and_jump_to_ends():
    terminal = printing_terminal(40)
    press(terminal, pygame.K_RETURN)
    press(terminal, pygame.K_SPACE, " ")
    assert terminal.pager.top == 13
    press(terminal, pygame.K_b, "b")
    assert terminal.pager.top == 0
    press(terminal, pygame.K_g, "G")
    assert terminal.pager.top == 40 - 13
    press(terminal, pygame.K_SPACE, " ")
    assert terminal.pager.top == 40 - 13
    press(terminal, pygame.K_g, "g")
    assert terminal.pager.top == 0
    terminal.scroll_down()
    assert terminal.pager.top == 1
    press(terminal, pygame.K_x, "x")
    assert terminal.input_buffer == ""


def test_closing_the_pager_keeps_the_viewed_page_in_scrollback():
    terminal = printing_terminal(40)
    press(terminal, pygame.K_RETURN)
    press(terminal, pygame.K_SPACE, " ")
    press(terminal, pygame.K_q, "q")
    assert terminal.pager is None
    assert len(terminal.output_buffer) == 41
    assert on_screen(terminal)[0] == "line 13"

    press(terminal, pygame.K_RETURN)
    terminal.pager = None
    assert terminal.scroll_position == 0


def test_pager_draws_styled_lines_and_status_bar():
    terminal = printing_terminal(0)
    terminal.output_buffer.append((("red", (230, 84, 72), None), (" on", (6, 18, 10), (46, 139, 87))))
    surface = pygame.Surface((880, 520))
    terminal.display(surface)
    terminal.pager = Pager(["a"] * 30, terminal.max_lines)
    terminal.display(surface)


def test_transient_output_is_always_paged_and_never_kept():
    from rich.text import Text

    from util.terminal_text import Transient

    terminal = printing_terminal(0)

    def run(command):
        terminal.output_buffer.append(f"> {command}")
        terminal.show(Transient(Text("short edition")))

    terminal.execute_command = run
    type_text(terminal, "news")
    press(terminal, pygame.K_RETURN)
    assert terminal.pager is not None and not terminal.pager.keep
    press(terminal, pygame.K_q, "q")
    assert terminal.output_buffer == ["> news"]

    tall = printing_terminal(40)
    press(tall, pygame.K_RETURN)
    press(tall, pygame.K_q, "q")
    assert len(tall.output_buffer) == 41


def test_news_intro_scans_then_opens_the_pager():
    from rich.text import Text

    from modes.planetary_mode.terminal import INTRO_HOLD_SECONDS, ROW_REVEAL_SECONDS
    from util.terminal_text import Transient

    terminal = printing_terminal(0)

    def run(command):
        terminal.output_buffer.append(f"> {command}")
        terminal.show(Transient(Text("front page"), intro=Text("wire one\nwire two")))

    terminal.execute_command = run
    press(terminal, pygame.K_RETURN)
    assert terminal.boot is not None and terminal.pager is None
    assert terminal.boot.rows_shown() == 0
    terminal.update(ROW_REVEAL_SECONDS)
    assert terminal.boot.rows_shown() == 1
    press(terminal, pygame.K_SPACE, " ")
    assert terminal.boot is None
    assert terminal.pager is not None and plain_pager(terminal) == ["front page"]

    terminal = printing_terminal(0)
    terminal.execute_command = run
    press(terminal, pygame.K_RETURN)
    terminal.update(2 * ROW_REVEAL_SECONDS + INTRO_HOLD_SECONDS)
    assert terminal.boot is None and terminal.pager is not None


def plain_pager(terminal):
    from util.terminal_text import plain
    return [plain(line) if not isinstance(line, str) else line for line in terminal.pager.lines]


def test_scan_escape_closes_the_pager_before_the_terminal():
    terminal = scan_terminal()
    closed = []
    terminal.star_system_mode.close_scan_terminal = lambda: closed.append(True)
    terminal.pager = Pager(["row"] * 30, terminal.max_lines)
    press(terminal, pygame.K_ESCAPE)
    assert terminal.pager is None
    assert terminal.active and not closed
    press(terminal, pygame.K_ESCAPE)
    assert closed
