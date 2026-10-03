"""Render Rich layouts offscreen into colored text spans the pygame terminals can draw."""
import io

from rich.console import Console

PALETTE = {
    "body": (46, 139, 87),
    "bright": (130, 230, 160),
    "dim": (30, 92, 60),
    "input": (107, 142, 35),
    "up": (255, 176, 0),
    "down": (230, 84, 72),
    "section": (90, 200, 220),
    "background": (6, 18, 10),
}

# TeleSys lacks these. Every replacement is one cell wide so Rich's column math still holds.
GLYPH_FALLBACKS = str.maketrans({
    "\u2026": ".",
    "\u25b2": "^",
    "\u25bc": "v",
    "\u2191": "^",
    "\u2193": "v",
    "\u2022": "*",
})


class Transient:
    """Output that is always shown in the pager and never kept in scrollback.

    Optional ``intro`` plays as a short scan animation before the pager opens.
    """

    def __init__(self, renderable, intro=None):
        self.renderable = renderable
        self.intro = intro

    def __rich__(self):
        return self.renderable


def color(name):
    """A palette entry as a Rich color string."""
    r, g, b = PALETTE[name]
    return f"rgb({r},{g},{b})"


def _mix(rgb, target, amount):
    return tuple(int(round(c + (t - c) * amount)) for c, t in zip(rgb, target))


def _span_colors(style):
    fg = bg = None
    if style is not None:
        if style.color is not None and not style.color.is_default:
            fg = tuple(style.color.get_truecolor())
        if style.bgcolor is not None and not style.bgcolor.is_default:
            bg = tuple(style.bgcolor.get_truecolor())
    fg = fg or PALETTE["body"]
    if style is not None:
        if style.bold:
            fg = _mix(fg, (255, 255, 255), 0.35)
        if style.dim:
            fg = _mix(fg, (0, 0, 0), 0.4)
        if style.reverse:
            fg, bg = (bg or PALETTE["background"]), fg
    return fg, bg


def to_lines(renderable, width):
    """Lines of (text, fg_rgb, bg_rgb_or_None) spans, with neighbors of the same colors merged."""
    console = Console(
        file=io.StringIO(),
        width=width,
        color_system="truecolor",
        force_terminal=True,
        legacy_windows=False,
        highlight=False,
        emoji=False,
    )
    lines = []
    for segments in console.render_lines(renderable, console.options.update_width(width), pad=False):
        spans = []
        for segment in segments:
            if segment.control or not segment.text:
                continue
            text = segment.text.translate(GLYPH_FALLBACKS)
            fg, bg = _span_colors(segment.style)
            if spans and spans[-1][1] == fg and spans[-1][2] == bg:
                spans[-1] = (spans[-1][0] + text, fg, bg)
            else:
                spans.append((text, fg, bg))
        lines.append(tuple(spans))
    return lines


def plain(line):
    """The text of a line, whether it is a plain string or a tuple of spans."""
    if isinstance(line, str):
        return line
    return "".join(span[0] for span in line)
