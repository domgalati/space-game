"""Enemy status, top right, while you have a target: its hull, shield and intent, and your shot.

    +-[ DOMINION RAIDER ]------------===-+
    | <#> RANGE 172 m                    |   <#> is the ship's sprite, at half size
    |     EFFECTIVE RANGE                |
    | HULL   █████░░░░░   41             |
    | SHIELD █░░░░░░░░░    6 RECHARGING  |
    | INTENT (*) FIRING NEXT TURN 65%    |
    | YOUR SHOT  65%  14 DMG             |
    | [F] FIRE  [R] SCAN  [TAB] NEXT     |
    +-===--------------------------------+
                               █ ▓ ▓       one pip per contact in sight, the target's lit

It opens on a target and wipes again when the target changes. When contact ends it holds,
dimmed, for LOST_TURNS turns; a kill breaks the frame apart instead.
"""
import math

import pygame

from util.config import SCREEN_WIDTH
from util.sprite_animation import TINT_LEVELS
from world.factions import faction_name

from ..combat import SCAN_RANGE, band, charged
from ..combat_fx import INTENT_GLYPHS, INTENT_WORDS
from .glyphs import draw_bar, draw_key, draw_text, effect, scramble, text_width
from .panel import Meter, Panel
from .ship_panel import (
    BAR_CELLS, BAR_COL, COLS, HULL_FLASH, LABEL_COL, TAG_COL, VALUE_CELLS, VALUE_COL, hull_colour,
)
from .theme import (
    BRIGHT, CELL_H, CELL_W, DANGER, FILL, LABEL, QUD, SHIELD, SHIELD_LOW, VALUE, WARN, WEAPON, blink, lift,
    shade,
)

ROWS = 9
MARGIN = 8
LOST_TURNS = 3  # the panel holds this many turns after contact ends
ICON = 24  # px: the ship's sprite, box-filtered to half size
TEXT_COL = LABEL_COL + 4  # range text starts clear of the icon
FRAME_SHADE = 0.35  # the frame is the faction colour, this much darker
LOST_DIM = 150
DIMMED = shade(VALUE, 0.55)
BAND_COLOURS = {"CLOSE": BRIGHT, "EFFECTIVE": WEAPON, "LONG": QUD["c"]}
LIVE, LOST, BREAKING = "live", "lost", "breaking"


def contact_title(vessel):
    return f"{faction_name(vessel.sponsor).upper()} {vessel.kind.upper()}"


class EnemyPanel:
    def __init__(self):
        self.panel = Panel(COLS, ROWS)
        self.shown = None  # the vessel on the panel
        self.lost_at = None  # turn contact ended, while the panel holds
        self.hull = Meter(flashes=True)
        self.shield = Meter()
        self._icons = {}

    def track(self, target, turn, now_ms):
        """Follow this frame's target (None with nothing in sight). Returns what the panel
        shows: LIVE, LOST (holding after contact ended), BREAKING (a kill), or None (closed)."""
        panel = self.panel
        if panel.broken_at is not None:
            if not panel.shattered(now_ms):
                return BREAKING
            self.close()
        if self.shown is not None and target is not self.shown and self.shown.ship.hull <= 0:
            panel.shatter(now_ms)
            return BREAKING
        if target is not None:
            if target is not self.shown:
                self.shown = target
                self.hull.reset()
                self.shield.reset()
                panel.open(now_ms)
            self.lost_at = None
            return LIVE
        if self.shown is None:
            return None
        if self.lost_at is None:
            self.lost_at = turn
        if turn - self.lost_at >= LOST_TURNS:
            self.close()
            return None
        return LOST

    def close(self):
        self.panel.close()
        self.shown = self.lost_at = None

    def hit(self, now_ms):
        """You landed a shot on it."""
        self.panel.flash(now_ms)

    def draw(self, screen, mode, now_ms):
        state = self.track(mode.current_target(), mode.clock.now, now_ms)
        if state is None:
            return
        topleft = (SCREEN_WIDTH - MARGIN - self.panel.width, MARGIN)
        if state == LIVE:
            self.draw_live(mode, now_ms)
        self.panel.blit(screen, topleft, now_ms, dim=LOST_DIM if state == LOST else 0)
        if state == LOST:
            self.draw_lost(screen, topleft, now_ms)
        elif state == LIVE:
            self.draw_pips(screen, mode, topleft)

    def draw_live(self, mode, now_ms):
        target = self.shown
        panel = self.panel
        panel.begin(contact_title(target), shade(target.colour, FRAME_SHADE), target.colour)
        distance = math.dist(mode.ship_center(), target.position)
        reach = band(distance)
        self.draw_range(target, distance, reach)
        if target.scanned:
            self.draw_hull(target.ship, now_ms)
            self.draw_shield(target.ship, now_ms)
            self.draw_intent(target.intent, now_ms)
        else:
            for row, label in ((3, "HULL"), (4, "SHIELD"), (5, "INTENT")):
                self.label(row, label)
                draw_text(panel.surface, panel.at(BAR_COL, row), scramble(BAR_CELLS + 1 + VALUE_CELLS, now_ms, row),
                          DIMMED)
        self.draw_shot(reach)
        several = len(mode.combat_targets()) > 1
        self.draw_keys(now_ms, reach is not None and charged(mode.player.ship),
                       not target.scanned and distance <= SCAN_RANGE, several)

    def label(self, row, text):
        draw_text(self.panel.surface, self.panel.at(LABEL_COL, row), text, LABEL)

    def draw_range(self, target, distance, reach):
        panel = self.panel
        x, y = panel.at(LABEL_COL, 1)
        panel.surface.blit(self.icon(target), (x, y + (2 * CELL_H - ICON) // 2))
        x, y = panel.at(TEXT_COL, 1)
        x += draw_text(panel.surface, (x, y), "RANGE ", LABEL)
        draw_text(panel.surface, (x, y), f"{int(distance)} m", WEAPON if reach else VALUE, glow=reach is not None)
        at = panel.at(TEXT_COL, 2)
        if reach:
            draw_text(panel.surface, at, f"{reach[2]} RANGE", BAND_COLOURS.get(reach[2], WEAPON))
        else:
            draw_text(panel.surface, at, "BEYOND WEAPON RANGE", DIMMED)

    def draw_hull(self, ship, now_ms, row=3):
        panel = self.panel
        shown = self.hull.update(ship.hull, now_ms)
        colour = hull_colour(ship.hull / ship.max_hull)
        self.label(row, "HULL")
        bar = HULL_FLASH if self.hull.flashing(now_ms) else colour
        draw_bar(panel.surface, panel.at(BAR_COL, row), BAR_CELLS, shown / ship.max_hull, bar)
        draw_text(panel.surface, panel.at(VALUE_COL, row), f"{math.ceil(shown):>{VALUE_CELLS}}", VALUE)

    def draw_shield(self, ship, now_ms, row=4):
        panel = self.panel
        shown = self.shield.update(ship.shield, now_ms)
        self.label(row, "SHIELD")
        draw_bar(panel.surface, panel.at(BAR_COL, row), BAR_CELLS, shown / ship.max_shield,
                 SHIELD if ship.shield_up else SHIELD_LOW)
        draw_text(panel.surface, panel.at(VALUE_COL, row), f"{int(shown):>{VALUE_CELLS}}", VALUE)
        at = panel.at(TAG_COL, row)
        if not charged(ship):
            draw_text(panel.surface, at, "RECHARGING", WARN)  # it can't fire: your opening
        else:
            draw_text(panel.surface, at, "UP" if ship.shield_up else "DOWN", SHIELD if ship.shield_up else DIMMED)

    def draw_intent(self, intent, now_ms, row=5):
        panel = self.panel
        kind, chance = intent
        self.label(row, "INTENT")
        firing = kind == "fire"
        colour = effect(DANGER, "blink", now_ms) if firing else WARN if kind == "ping" else VALUE
        x, y = panel.at(BAR_COL, row)
        x += draw_text(panel.surface, (x, y), f"{INTENT_GLYPHS.get(kind, '..')} {INTENT_WORDS.get(kind, '')}",
                       colour, glow=firing and blink(now_ms))
        if firing and chance is not None:
            draw_text(panel.surface, (x + CELL_W, y), f"{round(chance * 100)}%", VALUE)

    def draw_shot(self, reach, row=6):
        panel = self.panel
        x, y = panel.at(LABEL_COL, row)
        x += draw_text(panel.surface, (x, y), "YOUR SHOT  ", LABEL)
        if reach is None:
            draw_text(panel.surface, (x, y), "OUT OF RANGE", DIMMED)
            return
        chance, damage, _ = reach
        x += draw_text(panel.surface, (x, y), f"{round(chance * 100)}%", WEAPON, glow=True)
        draw_text(panel.surface, (x + 2 * CELL_W, y), f"{damage} DMG", VALUE)

    def draw_keys(self, now_ms, can_fire, can_scan, several, row=7):
        panel = self.panel
        x, y = panel.at(LABEL_COL, row)
        for key, word, lit in (("F", "FIRE", can_fire), ("R", "SCAN", can_scan), ("TAB", "NEXT", several)):
            x += draw_key(panel.surface, (x, y), key, LABEL, now_ms, lit=lit, pulse=key != "TAB")
            x += CELL_W
            x += draw_text(panel.surface, (x, y), word, VALUE if lit else DIMMED) + 2 * CELL_W

    def icon(self, vessel):
        """The vessel's current sprite frame, nose up, damage-tinted, at half size."""
        sprite = vessel.sprite()
        tint = min(TINT_LEVELS - 1, int((1 - vessel.ship.hull / vessel.ship.max_hull) * TINT_LEVELS))
        key = (vessel.kind, vessel.sponsor, sprite.current_frame, tint)
        icon = self._icons.get(key)
        if icon is None:
            icon = self._icons[key] = pygame.transform.smoothscale(sprite.get_frame("north", tint), (ICON, ICON))
        return icon

    def draw_lost(self, screen, topleft, now_ms):
        text = "CONTACT LOST"
        x = topleft[0] + (self.panel.width - text_width(text)) // 2
        y = topleft[1] + (self.panel.height - CELL_H) // 2
        plate = pygame.Surface((text_width(text) + 2 * CELL_W, CELL_H), pygame.SRCALPHA)
        plate.fill(FILL)
        screen.blit(plate, (x - CELL_W, y))
        draw_text(screen, (x, y), text, effect(WARN, "blink", now_ms), glow=blink(now_ms))

    def draw_pips(self, screen, mode, topleft):
        """One pip per armed contact in sight, nearest first, under the frame; the target's lit."""
        contacts = mode.combat_targets()
        if len(contacts) < 2:
            return
        width = (2 * len(contacts) + 1) * CELL_W
        x = topleft[0] + self.panel.width - CELL_W // 2 - width
        y = topleft[1] + self.panel.height
        plate = pygame.Surface((width, CELL_H), pygame.SRCALPHA)
        plate.fill(FILL)
        screen.blit(plate, (x, y))
        for i, vessel in enumerate(contacts):
            colour = lift(vessel.colour, 0.2) if vessel is self.shown else shade(vessel.colour, 0.55)
            draw_bar(screen, (x + (2 * i + 1) * CELL_W, y), 1, 1.0 if vessel is self.shown else 0.5, colour)
