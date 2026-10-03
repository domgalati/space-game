"""The action strip, bottom centre: what you can do here and what's acting on you.

    +--------------------------===-+
    | [E] DOCK · ETHEORA           |     a corridor: the keycap pulses
    +-===--------------------------+

It shows the most important item, with a second as a slimmer line above it. A corridor
(dock, then salvage, then scan) beats solar heat, which beats atmosphere. There is no glare
item: the glare is the sun's heat zone, so the heat band and the ship panel's GLARE chip
already say it.
"""
import math
import zlib
from collections import namedtuple

import pygame

from util.config import SCREEN_HEIGHT, SCREEN_WIDTH

from ..scan_terminal import has_landing_map
from .glyphs import draw_key, draw_text, key_width, text_width
from .panel import Panel
from .theme import CELL_H, CELL_W, FACTIONS, FILL, HEAT, LABEL, VALUE, WARN, lift, pulsing, shade

Action = namedtuple("Action", "key verb name colour kind")  # kind: "corridor", "heat" or "atmosphere"
SEP = " · "  # ·
MARGIN = 8
SHIMMER = "~^-'.,"
SHIMMER_MS = 110


def corridor_rank(body):
    """Dock beats salvage beats scan, when corridors overlap."""
    if getattr(body, "obj_type", None) == "Wreck":
        return 1 if not body.empty() else 2
    return 0 if has_landing_map(body) else 2


def corridor_action(body):
    if getattr(body, "obj_type", None) == "Wreck":
        verb = "SALVAGE" if not body.empty() else "SCAN"
        return Action("E", verb, body.name.upper(), FACTIONS.get(body.sponsor, LABEL), "corridor")
    verb = "DOCK" if has_landing_map(body) else "SCAN"
    return Action("E", verb, body.name.upper(), FACTIONS.get(body.planet_guild, LABEL), "corridor")


def actions(mode, atmosphere_burn):
    """Everything the strip could show here, most important first."""
    found = []
    body = mode.check_collision()
    if body is not None:
        found.append(corridor_action(body))
    heat = mode.selected_system.heat_at(mode.ship_center())
    if heat > 0:
        found.append(Action(None, "SOLAR HEAT", f"-{math.ceil(heat)} / TURN", HEAT, "heat"))
    if mode.in_atmosphere():
        found.append(Action(None, "ATMOSPHERE", f"FUEL x{atmosphere_burn:g}", WARN, "atmosphere"))
    return found


def _width(action):
    words = f"{action.verb}{SEP}{action.name}"
    return text_width(words) + (key_width(action.key) + CELL_W if action.key else 0)


class ActionStrip:
    def __init__(self):
        self.shown = None  # what the main item is, to wipe the strip open when it changes
        self._panels = {}

    def draw(self, screen, mode, now_ms, atmosphere_burn):
        found = actions(mode, atmosphere_burn)
        if not found:
            self.shown = None
            return
        main = found[0]
        cols = _width(main) // CELL_W + 4
        panel = self._panels.get(cols)
        if panel is None:
            panel = self._panels[cols] = Panel(cols, 3)
        identity = (main.kind, main.verb, main.name if main.kind == "corridor" else None)
        if identity != self.shown:  # a new item wipes in; a heat reading that changes doesn't
            panel.open(now_ms)
            self.shown = identity
        self.draw_main(panel, main, now_ms)
        top = SCREEN_HEIGHT - MARGIN - panel.height
        panel.blit(screen, ((SCREEN_WIDTH - panel.width) // 2, top), now_ms)
        if len(found) > 1:
            self.draw_second(screen, found[1], top, now_ms)

    def draw_main(self, panel, action, now_ms):
        colour = pulsing(action.colour, now_ms, low=0.7) if action.kind == "atmosphere" else action.colour
        panel.begin("", shade(action.colour, 0.4))
        if action.kind == "heat":
            shimmer(panel, action.colour, now_ms)
        x, y = panel.at(2, 1)
        if action.key:
            x += draw_key(panel.surface, (x, y), action.key, action.colour, now_ms, pulse=True) + CELL_W
            x += draw_text(panel.surface, (x, y), action.verb + SEP, VALUE)
            draw_text(panel.surface, (x, y), action.name, colour, glow=True)
        else:
            x += draw_text(panel.surface, (x, y), action.verb, colour, glow=True)
            draw_text(panel.surface, (x, y), SEP + action.name, lift(colour, 0.3))

    def draw_second(self, screen, action, top, now_ms):
        """The runner-up, as one slim line on a plate above the strip."""
        words = f"{action.verb}{SEP}{action.name}"
        if action.key:
            words = f"[{action.key}] {words}"
        plate = pygame.Surface((text_width(words) + 2 * CELL_W, CELL_H), pygame.SRCALPHA)
        plate.fill(FILL)
        x = (SCREEN_WIDTH - plate.get_width()) // 2
        y = top - CELL_H - 2
        screen.blit(plate, (x, y))
        draw_text(screen, (x + CELL_W, y), words, shade(action.colour, 0.15))


def shimmer(panel, colour, now_ms):
    """Heat haze: noise glyphs crawl along the strip's top and bottom edges."""
    step = now_ms // SHIMMER_MS
    for row in (0, panel.rows - 1):
        for col in range(1, panel.cols - 1):
            h = zlib.crc32(f"{col},{row},{step}".encode())
            if h % 3:
                continue
            x, y = panel.at(col, row)
            panel.surface.fill(FILL, (x, y, CELL_W, CELL_H))
            draw_text(panel.surface, (x, y), SHIMMER[h % len(SHIMMER)], lift(colour, 0.3) if h % 2 else colour)
