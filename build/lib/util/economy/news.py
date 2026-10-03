"""Market wire: event names and prices stay fixed, the sentences around them do not."""
import random

from rich import box
from rich.console import Group
from rich.panel import Panel
from rich.rule import Rule
from rich.table import Table
from rich.text import Text

from util.terminal_text import color

MASTHEAD = "THE NEXUS WIRE"
EDITIONS = ("SOL MARKETS", "LATE EDITION", "MORNING EDITION", "DOCKSIDE EDITION", "FINAL EDITION")

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

SWING_COUNT = 5
BAR_FULL_PERCENT = 80
CARD_BAR_CELLS = 6
SWING_BAR_CELLS = 10
TWO_UP_MIN_WIDTH = 70
EIGHTHS = "\u258f\u258e\u258d\u258c\u258b\u258a\u2589"
FULL_BLOCK = "\u2588"


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


def _moves(place, goods, effects):
    """(good, price, change, percent) for each listed good this market actually trades."""
    moves = []
    for good, spec in (effects or {}).items():
        change = (spec or {}).get("priceChange") or ""
        if good not in goods or not change:
            continue
        moves.append((good, event_price(goods[good]["basePrice"], change), change, _percent(change)))
    return moves


def _stories(data):
    """(place, event, moves) for every event with at least one effect on its own market."""
    stories = []
    for place, market in (data or {}).items():
        market = market or {}
        goods = market.get("goods") or {}
        for event, effects in (market.get("events") or {}).items():
            moves = _moves(place, goods, effects)
            if moves:
                stories.append((place, event, moves))
    return stories


def _masthead(rng):
    grid = Table.grid(expand=True)
    grid.add_column(justify="left")
    grid.add_column(justify="right")
    style = f"{color('background')} on {color('bright')}"
    grid.add_row(Text(f" {MASTHEAD}"), Text(f"{rng.choice(EDITIONS)} "), style=style)
    return Group(grid, Rule(characters="\u2550", style=color("dim")))


def _swings(stories):
    """The largest moves, one per good per market."""
    biggest = {}
    for place, _event, moves in stories:
        for good, price, change, percent in moves:
            held = biggest.get((good, place))
            if held is None or abs(percent) > abs(held[4]):
                biggest[(good, place)] = (good, place, price, change, percent)
    ranked = sorted(biggest.values(), key=lambda row: -abs(row[4]))[:SWING_COUNT]
    table = Table(
        box=None, expand=True, pad_edge=False, show_edge=False,
        header_style=color("dim"), title=None,
    )
    table.add_column("BIGGEST SWINGS", style=color("bright"), ratio=1)
    table.add_column("MARKET", style=color("body"), no_wrap=True)
    table.add_column("PRICE", justify="right", no_wrap=True)
    table.add_column("MOVE", justify="right", no_wrap=True)
    table.add_column("", width=SWING_BAR_CELLS, no_wrap=True)
    for good, place, price, change, percent in ranked:
        table.add_row(good, place, Text(f"${price}", style=color("bright")),
                      Text(change, style=_tone(percent)), bar(percent, SWING_BAR_CELLS))
    return table


def _verb(percent, rng):
    if percent > 0:
        return rng.choice(UP_VERBS)
    if percent < 0:
        return rng.choice(DOWN_VERBS)
    return rng.choice(FLAT_VERBS)


def _card(place, event, moves, rng):
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


def render_news(data, rng=random):
    """A front page of every market event and the price each one sets, freshly worded each read."""
    stories = _stories(data)
    parts = [_masthead(rng)]
    if not stories:
        parts.append(Text("No market events on file.", style=color("body")))
        return Group(*parts)
    parts.append(_swings(stories))
    for place in dict.fromkeys(place for place, _event, _moves in stories):
        parts.append(Text(""))
        parts.append(Rule(Text(f" {place.upper()} ", style=f"bold {color('section')}"),
                          align="left", characters="\u2500", style=color("dim")))
        cards = [_card(p, event, moves, rng) for p, event, moves in stories if p == place]
        parts.append(_CardGrid(cards))
    return Group(*parts)
