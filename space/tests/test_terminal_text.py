from rich.text import Text

from util.terminal_text import PALETTE, color, plain, to_lines


def test_colored_text_maps_to_rgb_spans():
    (line,) = to_lines(Text.assemble(("up", color("up")), " plain"), 20)
    assert line[0] == ("up", PALETTE["up"], None)
    assert line[1] == (" plain", PALETTE["body"], None)


def test_background_and_reverse_produce_bg():
    (on_line,) = to_lines(Text("bar", style=f"{color('background')} on {color('bright')}"), 10)
    assert on_line[0] == ("bar", PALETTE["background"], PALETTE["bright"])

    (reversed_line,) = to_lines(Text("rev", style=f"reverse {color('down')}"), 10)
    assert reversed_line[0] == ("rev", PALETTE["background"], PALETTE["down"])


def test_missing_glyphs_fall_back_one_cell_wide():
    (line,) = to_lines(Text("a\u2026b \u25b2\u25bc \u2022"), 20)
    assert plain(line) == "a.b ^v *"


def test_lines_wrap_to_width():
    lines = to_lines(Text("word " * 20), 24)
    assert len(lines) > 1
    assert all(len(plain(line)) <= 24 for line in lines)
