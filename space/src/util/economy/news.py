"""The front page: what the player has heard from the markets they checked recently.

Event names and prices stay fixed; the sentences around them are reworded on every read.
"""
import random

from rich import box
from rich.console import Group
from rich.panel import Panel
from rich.rule import Rule
from rich.table import Table
from rich.text import Text

from util.economy.news_feed import FRESH_TICKS
from util.terminal_text import Transient, color

MASTHEAD = "THE NEXUS WIRE"
EDITIONS = ("LATE EDITION", "MORNING EDITION", "DOCKSIDE EDITION", "FINAL EDITION", "SOL MARKETS")

LEADS = (
    "Wire from {place}: {event}.",
    "Traders on {place} won't shut up about {event}.",
    "{event}. That's the story off {place}.",
    "Dispatch from {place}. {event}.",
    "Heard it on the {place} band: {event}.",
    "The {place} boards lit up over {event}.",
    "Word out of {place}: {event}.",
    "A clerk on {place} posted {event} on the board.",
)

# Verbs only. Good and dollar price are filled in so they cannot be dropped.
UP_VERBS = ("climbing to", "bid up to", "pushed to", "up to")
DOWN_VERBS = ("sliding to", "marked down to", "cut to", "down to")
FLAT_VERBS = ("holding at", "unchanged at")

MAX_LINES = 52  # four terminal pages
MOVER_COUNT = 5
BAR_FULL_PERCENT = 80
CARD_BAR_CELLS = 6
MOVER_BAR_CELLS = 10
TWO_UP_MIN_WIDTH = 70
FOOTER_LINES = 2
EIGHTHS = "\u258f\u258e\u258d\u258c\u258b\u258a\u2589"
FULL_BLOCK = "\u2588"

NO_WIRE = "No fresh wire. Scan a market or land to pick up news."
QUIET_WIRE = "Quiet wire. Nothing new from the markets you've checked."


def event_price(base_price, price_change):
    """Price an event sets from base. The percent's sign is applied once.

    ``int("-10%")`` is -10, so the sign is stripped before the magnitude is used.
    """
    magnitude = int(price_change.replace("%", "").replace("+", "").replace("-", "")) / 100
    if "+" in price_change:
        new_price = base_price * (1 + magnitude)
    elif "-" in price_change:
        new_price = base_price * (1 - magnitude)
    else:
        new_price = base_price
    return int(round(new_price))


def _percent(change):
    return int(change.replace("%", "").replace("+", ""))


def _tone(percent):
    if percent > 0:
        return color("up")
    if percent < 0:
        return color("down")
    return color("dim")


def bar(percent, cells):
    """Eighth-block bar, full at BAR_FULL_PERCENT."""
    eighths = round(min(abs(percent), BAR_FULL_PERCENT) / BAR_FULL_PERCENT * cells * 8)
    if percent and not eighths:
        eighths = 1
    text = FULL_BLOCK * (eighths // 8)
    if eighths % 8:
        text += EIGHTHS[eighths % 8 - 1]
    return Text(text, style=_tone(percent))


def age_text(age):
    if age == 0:
        return "this landing"
    return f"{age} landing ago" if age == 1 else f"{age} landings ago"


def _heading(title):
    return Rule(Text(f" {title} ", style=f"bold {color('section')}"),
                align="left", characters="\u2500", style=color("dim"))


def _masthead(tick, rng):
    grid = Table.grid(expand=True)
    grid.add_column(justify="left")
    grid.add_column(justify="right")
    style = f"{color('background')} on {color('bright')}"
    grid.add_row(Text(f" {MASTHEAD}"), Text(f"LANDING {tick}  {rng.choice(EDITIONS)} "), style=style)
    return Group(grid, Rule(characters="\u2550", style=color("dim")))


def wire_check(feed, places):
    """Short sync readout shown as a scan animation before the front page."""
    lines = [
        Text(" POLLING ACTIVE WIRES", style=f"bold {color('bright')}"),
        Text("\u2550" * 28, style=color("dim")),
    ]
    for place, age in feed.market_status(places):
        if age is None:
            status = Text("no contact", style=color("dim"))
        elif age > FRESH_TICKS:
            status = Text(f"stale, {age_text(age)}", style=color("down"))
        elif age == 0:
            status = Text("live", style=color("up"))
        else:
            status = Text(f"checked {age_text(age)}", style=color("body"))
        row = Text(f" {place:<14}", style=color("bright"))
        row.append(" ... ", style=color("dim"))
        row.append_text(status)
        lines.append(row)
    lines.append(Text(""))
    lines.append(Text(" SYNC COMPLETE", style=f"bold {color('section')}"))
    return Group(*lines)


def _movers(feed):
    """Biggest gaps between the price last seen and base, across markets still fresh."""
    rows = []
    for place, seen in feed.intel.items():
        if not feed.is_fresh(place):
            continue
        for good, info in seen["goods"].items():
            base = info.get("base") or 0
            if base:
                percent = int(round((info["price"] - base) / base * 100))
                if percent:
                    rows.append((good, place, info["price"], percent))
    if not rows:
        return None
    rows.sort(key=lambda row: (-abs(row[3]), row[1], row[0]))
    table = Table(box=None, expand=True, pad_edge=False, show_edge=False, header_style=color("dim"))
    table.add_column("GOOD", style=color("bright"), ratio=1)
    table.add_column("MARKET", style=color("body"), no_wrap=True)
    table.add_column("PRICE", justify="right", no_wrap=True)
    table.add_column("VS BASE", justify="right", no_wrap=True)
    table.add_column("", width=MOVER_BAR_CELLS, no_wrap=True)
    for good, place, price, percent in rows[:MOVER_COUNT]:
        table.add_row(good, place, Text(f"${price}", style=color("bright")),
                      Text(f"{percent:+d}%", style=_tone(percent)), bar(percent, MOVER_BAR_CELLS))
    return Group(_heading("MARKET MOVERS"), table)


def _verb(percent, rng):
    if percent > 0:
        return rng.choice(UP_VERBS)
    if percent < 0:
        return rng.choice(DOWN_VERBS)
    return rng.choice(FLAT_VERBS)


def _card(feed, story, rng):
    place, event = story["place"], story["event"]
    moves = [(move["good"], move["price"], move["change"], _percent(move["change"])) for move in story["moves"]]

    lead = Text(rng.choice(LEADS).format(place=place, event=event), style=color("body"))
    good, price, _change, percent = max(moves, key=lambda move: abs(move[3]))
    lead.append(f" {good} {_verb(percent, rng)} ${price}.", style=color("body"))

    rows = Table.grid(expand=True, padding=(0, 1))
    rows.add_column(ratio=1, style=color("bright"))
    rows.add_column(justify="right", no_wrap=True, style=color("bright"))
    rows.add_column(justify="right", no_wrap=True)
    rows.add_column(width=CARD_BAR_CELLS, no_wrap=True)
    for good, price, change, percent in moves:
        rows.add_row(good, f"${price}", Text(change, style=_tone(percent)), bar(percent, CARD_BAR_CELLS))

    return Panel(
        Group(lead, rows),
        title=Text(event.upper(), style=f"bold {color('bright')}"),
        title_align="left",
        subtitle=Text(f"{place}, {age_text(feed.tick - story['tick'])}", style=color("dim")),
        subtitle_align="right",
        box=box.SQUARE,
        border_style=color("dim"),
        padding=(0, 1),
    )


class _CardGrid:
    """Story cards two-up on a wide terminal, stacked on a narrow one."""

    def __init__(self, cards):
        self.cards = cards

    def __rich_console__(self, console, options):
        columns = 2 if options.max_width >= TWO_UP_MIN_WIDTH else 1
        grid = Table.grid(expand=True, padding=(0, 1))
        for _ in range(columns):
            grid.add_column(ratio=1)
        for start in range(0, len(self.cards), columns):
            row = self.cards[start:start + columns]
            grid.add_row(*row, *([""] * (columns - len(row))))
        yield grid


class _FrontPage:
    """Fixed sections, then as many story cards as fit in MAX_LINES at the terminal's real width."""

    def __init__(self, fixed, cards):
        self.fixed = fixed
        self.cards = cards

    def __rich_console__(self, console, options):
        def height(renderable):
            return len(console.render_lines(renderable, options, pad=False))

        used = sum(height(part) for part in self.fixed)
        yield from self.fixed
        if not self.cards:
            return
        heading = Group(Text(""), _heading("THE WIRE"))
        budget = MAX_LINES - used - height(heading) - FOOTER_LINES
        shown = 0
        while shown < len(self.cards) and height(_CardGrid(self.cards[:shown + 1])) <= budget:
            shown += 1
        if shown:
            yield heading
            yield _CardGrid(self.cards[:shown])
        held = len(self.cards) - shown
        if held:
            noun = "story" if held == 1 else "stories"
            yield Text("")
            yield Text(f"{held} older {noun} held. Scan markets for fresh news.", style=color("dim"))


def render_news(feed, places=(), rng=random):
    """Front page for ``feed``. Wire status plays as a brief intro scan, not on the page."""
    places = list(places or ())
    if feed is None:
        return Transient(Group(_masthead(0, rng), Text(NO_WIRE, style=color("body"))))

    intro = wire_check(feed, places)
    fixed = [_masthead(feed.tick, rng)]
    if not any(feed.is_fresh(place) for place in feed.intel):
        fixed.extend([Text(""), Text(NO_WIRE, style=color("body"))])
        return Transient(_FrontPage(fixed, []), intro=intro)

    movers = _movers(feed)
    if movers is not None:
        fixed.extend([Text(""), movers])
    stories = feed.known_stories()
    if not stories:
        fixed.extend([Text(""), Text(QUIET_WIRE, style=color("body"))])
    return Transient(
        _FrontPage(fixed, [_card(feed, story, rng) for story in stories]),
        intro=intro,
    )
