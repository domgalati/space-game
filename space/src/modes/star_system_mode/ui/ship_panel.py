"""Ship status, top left and always on: hull, shield, fuel, signal, credits, cargo and chips.

    +-[ BARGE ]----------------------===-+
    | HULL   ██████████  100             |
    | SHIELD ██████▓░░░   64 (UP)        |
    | FUEL   ██████████ 1000             |
    | SIGNAL ███▒░░░░░░  700 QUIET       |
    | $1500                 CARGO 12/100 |
    | [HUNTED] [PATROL]                  |
    +-===--------------------------------+
"""
import math

from ..combat import charged
from ..sensors import LOUD_AT, SIGNATURE_DARK, SIGNATURE_MAX
from .glyphs import draw_bar, draw_chip, draw_text, effect, text_width
from .panel import Meter, Panel
from .theme import (
    BRIGHT, DANGER, GOOD, HEAT, LABEL, PATROL, QUD, SHIELD, SHIELD_LOW, VALUE, WARN, blink, lift, pulsing,
    shade,
)

TITLE = "BARGE"
COLS, ROWS = 38, 8
POSITION = (8, 8)
LABEL_COL, BAR_COL, VALUE_COL, TAG_COL = 2, 9, 20, 25
LAST_COL = COLS - 3  # rightmost content cell; one cell of padding inside the border
BAR_CELLS = 10
VALUE_CELLS = 4
DAMAGED_HULL = 0.5  # hull bar turns amber below this share
CRITICAL_HULL = 0.25  # and red, blinking, below this
LOW_FUEL = 20
HULL_FLASH = lift(DANGER, 0.3)
SHIELD_FLASH = BRIGHT
QUIET = QUD["c"]
DIMMED = shade(VALUE, 0.55)


def hull_colour(share):
    """Green, amber below half, red below a quarter."""
    if share >= DAMAGED_HULL:
        return GOOD
    return WARN if share >= CRITICAL_HULL else DANGER


def signature_word(loudness):
    if loudness <= SIGNATURE_DARK:
        return "DARK"
    return "QUIET" if loudness < LOUD_AT else "LOUD"


def signal_colour(loudness):
    """Teal while pings only find you close in, amber past halfway, red at full range."""
    share = (loudness - SIGNATURE_DARK) / (LOUD_AT - SIGNATURE_DARK)
    if share < 0.5:
        return QUIET
    return WARN if share < 1 else DANGER


def status_chips(mode):
    """(label, colour, effect) for the chip row, most urgent first."""
    me = mode.ship_center()
    chips = []
    if mode.hunted():
        chips.append(("HUNTED", WARN, "pulse"))
    if mode.sensors.blind(me):
        chips.append(("GLARE", HEAT, None))
    if mode.selected_system.in_patrol_zone(me):
        chips.append(("PATROL", PATROL, None))
    if mode.boosting:
        chips.append(("BOOST", QUD["W"], None))
    elif mode.on_charted_ring():
        chips.append(("RING", QUIET, None))
    return chips


def _value(surface, panel, row, number, colour, glow=False):
    draw_text(surface, panel.at(VALUE_COL, row), f"{number:>{VALUE_CELLS}}", colour, glow=glow)


class ShipPanel:
    def __init__(self):
        self.panel = Panel(COLS, ROWS)
        self.hull = Meter(flashes=True)
        self.shield = Meter()

    def draw(self, screen, mode, now_ms):
        panel = self.panel
        if not panel.is_open:
            panel.open(now_ms)
        panel.begin(TITLE)
        ship = mode.player.ship
        self.draw_hull(ship, now_ms)
        self.draw_shield(ship, now_ms, now_ms < mode.shield_flash_until)
        self.draw_fuel(ship, now_ms)
        self.draw_signal(mode)
        self.draw_money(mode.player)
        self.draw_chips(mode, now_ms)
        panel.blit(screen, POSITION, now_ms)

    def label(self, row, text):
        draw_text(self.panel.surface, self.panel.at(LABEL_COL, row), text, LABEL)

    def draw_hull(self, ship, now_ms, row=1):
        panel = self.panel
        shown = self.hull.update(ship.hull, now_ms)
        share = ship.hull / ship.max_hull
        critical = share < CRITICAL_HULL
        colour = hull_colour(share)
        if critical:
            colour = effect(colour, "blink", now_ms)
        bar = HULL_FLASH if self.hull.flashing(now_ms) else colour
        self.label(row, "HULL")
        draw_bar(panel.surface, panel.at(BAR_COL, row), BAR_CELLS, shown / ship.max_hull, bar)
        _value(panel.surface, panel, row, math.ceil(shown), colour if critical else VALUE,
               glow=critical and blink(now_ms))

    def draw_shield(self, ship, now_ms, absorbing, row=2):
        panel = self.panel
        shown = self.shield.update(ship.shield, now_ms)
        colour = SHIELD if ship.shield_up else SHIELD_LOW
        self.label(row, "SHIELD")
        draw_bar(panel.surface, panel.at(BAR_COL, row), BAR_CELLS, shown / ship.max_shield,
                 SHIELD_FLASH if absorbing else colour)
        _value(panel.surface, panel, row, int(shown), VALUE)
        at = panel.at(TAG_COL, row)
        if not charged(ship):
            draw_text(panel.surface, at, "NO CHARGE", WARN)
        elif ship.shield_up:
            draw_text(panel.surface, at, "(UP)", pulsing(lift(SHIELD, 0.2), now_ms), glow=True)
        else:
            draw_text(panel.surface, at, "DOWN", DIMMED)

    def draw_fuel(self, ship, now_ms, row=3):
        panel = self.panel
        colour = VALUE if ship.fuel >= LOW_FUEL else WARN
        self.label(row, "FUEL")
        draw_bar(panel.surface, panel.at(BAR_COL, row), BAR_CELLS, ship.fuel / ship.max_fuel, colour)
        _value(panel.surface, panel, row, int(ship.fuel), colour)
        if ship.on_reserve:
            draw_chip(panel.surface, panel.at(TAG_COL, row), "RESERVE", effect(DANGER, "blink", now_ms))

    def draw_signal(self, mode, row=4):
        panel = self.panel
        loudness = mode.player_signature()
        colour = signal_colour(loudness)
        self.label(row, "SIGNAL")
        draw_bar(panel.surface, panel.at(BAR_COL, row), BAR_CELLS, loudness / SIGNATURE_MAX, colour)
        _value(panel.surface, panel, row, int(loudness), VALUE)
        word = signature_word(loudness)
        x, y = panel.at(TAG_COL, row)
        x += draw_text(panel.surface, (x, y), word, colour)
        action = {"ping": "PING", "fire": "FIRE"}.get(mode.last_action)
        if action:
            draw_text(panel.surface, (x + text_width(" "), y), action, WARN)

    def draw_money(self, player, row=5):
        panel = self.panel
        draw_text(panel.surface, panel.at(LABEL_COL, row), f"${player.currency}", VALUE, glow=True)
        cargo = player.ship.cargo
        held = cargo.get_total_quantity()
        load = f"{held}/{cargo.capacity}"
        x, y = panel.at(LAST_COL + 1, row)
        x -= text_width(load)
        draw_text(panel.surface, (x, y), load, WARN if held >= cargo.capacity else VALUE)
        draw_text(panel.surface, (x - text_width("CARGO "), y), "CARGO", LABEL)

    def draw_chips(self, mode, now_ms, row=6):
        panel = self.panel
        x, y = panel.at(LABEL_COL, row)
        right = panel.at(LAST_COL + 1, row)[0]
        for label, colour, kind in status_chips(mode):
            if x + text_width(label) + 2 * text_width(" ") > right:
                break
            x += draw_chip(panel.surface, (x, y), label, effect(colour, kind, now_ms)) + text_width(" ")
