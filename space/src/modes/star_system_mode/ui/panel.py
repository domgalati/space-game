"""Glyph-bordered panels, and the meters that animate the values inside them.

A panel draws offscreen on the 8x16 grid, then goes to the screen with its effects: a
scanline wipe as it opens, a flash when it's hit, a dimmed hold, and a break-up.
"""
import pygame

from .glyphs import draw_text, text_width
from .theme import (
    BLACK, BRIGHT, CELL_H, CELL_W, COUNT_MS, FILL, FLASH_MS, FRAME, LABEL, WIPE_MS, lift,
)

CORNER_LIFT = 0.3  # corners a little brighter than the edges
ACCENT_CELLS = 3  # a short "===" run on the top and bottom edges
WIPE_LINE = 2  # px, the bright line leading a wipe
WIPE_ALPHA = 200
FLASH_ALPHA = 80
BREAK_MS = 600
BREAK_FALL = 28  # px the last pieces drift down as a panel breaks up
CHROME_CACHE = 16


class Meter:
    """A value as its bar shows it. A drop counts down over COUNT_MS and can flash the bar;
    a rise jumps straight there."""

    def __init__(self, flashes=False):
        self.flashes = flashes
        self.reset()

    def reset(self):
        self.start = self.end = None
        self.started_at = 0
        self.flash_until = 0

    def update(self, value, now_ms):
        """Take this frame's reading; returns the value to show."""
        if self.end is None or value > self.end:
            self.start = self.end = value
        elif value < self.end:
            self.start = self.shown(now_ms)
            self.end = value
            self.started_at = now_ms
            if self.flashes:
                self.flash_until = now_ms + FLASH_MS
        return self.shown(now_ms)

    def shown(self, now_ms):
        if self.end is None:
            return 0
        progress = min(1.0, max(0, now_ms - self.started_at) / COUNT_MS)
        return self.start + (self.end - self.start) * progress

    def flashing(self, now_ms):
        return now_ms < self.flash_until


def _noise(col, row):
    h = (col * 73856093) ^ (row * 19349663)
    h = ((h ^ (h >> 13)) * 1274126177) & 0xFFFFFFFF
    return ((h ^ (h >> 16)) & 0xFFFF) / 0xFFFF


class Panel:
    """A box of `cols` x `rows` glyph cells: translucent fill, glyph border, header tab.

    Each frame, `begin` clears it to its border and the owner draws rows into `surface`
    (`at` turns cells into pixels). An owner that stops drawing leaves the last frame up,
    frozen, which is what a hold or a break-up shows.
    """

    def __init__(self, cols, rows):
        self.cols, self.rows = cols, rows
        self.surface = pygame.Surface((cols * CELL_W, rows * CELL_H), pygame.SRCALPHA)
        self.opened_at = None
        self.broken_at = None
        self.flash_until = 0
        self.flash_colour = BRIGHT
        self._chrome = {}

    @property
    def width(self):
        return self.surface.get_width()

    @property
    def height(self):
        return self.surface.get_height()

    @property
    def is_open(self):
        return self.opened_at is not None

    def at(self, col, row):
        return col * CELL_W, row * CELL_H

    def open(self, now_ms):
        """Open with a scanline wipe, or wipe again if it's already open."""
        self.opened_at = now_ms
        self.broken_at = None

    def close(self):
        self.opened_at = self.broken_at = None

    def flash(self, now_ms, colour=BRIGHT):
        self.flash_until = now_ms + FLASH_MS
        self.flash_colour = colour

    def shatter(self, now_ms):
        """Break the frozen last frame apart over BREAK_MS."""
        self.broken_at = now_ms

    def shattered(self, now_ms):
        return self.broken_at is not None and now_ms - self.broken_at >= BREAK_MS

    def begin(self, title, frame=FRAME, title_colour=LABEL):
        """Clear to the fill, border and header tab, ready for this frame's rows."""
        key = (title, frame, title_colour)
        chrome = self._chrome.get(key)
        if chrome is None:
            if len(self._chrome) >= CHROME_CACHE:
                self._chrome.clear()
            chrome = self._chrome[key] = self._draw_chrome(title, frame, title_colour)
        self.surface.fill((0, 0, 0, 0))
        self.surface.blit(chrome, (0, 0))

    def _draw_chrome(self, title, frame, title_colour):
        surface = pygame.Surface(self.surface.get_size(), pygame.SRCALPHA)
        # The fill runs under the border too, so a dark frame still reads over a bright planet.
        surface.fill(FILL)
        corner = lift(frame, CORNER_LIFT)
        run = self.cols - 2 - ACCENT_CELLS - 1
        top = "-" * run + "=" * ACCENT_CELLS + "-"  # accents at the top right and bottom left
        for row, edge in ((0, top), (self.rows - 1, top[::-1])):
            draw_text(surface, self.at(0, row), "+", corner)
            draw_text(surface, self.at(1, row), edge, frame)
            draw_text(surface, self.at(self.cols - 1, row), "+", corner)
        for row in range(1, self.rows - 1):
            draw_text(surface, self.at(0, row), "|", frame)
            draw_text(surface, self.at(self.cols - 1, row), "|", frame)
        if title:
            tab = f"[ {title} ]"
            x, y = self.at(2, 0)
            surface.fill(FILL, (x, y, text_width(tab), CELL_H))  # clear the edge glyphs under the tab
            x += draw_text(surface, (x, y), "[ ", corner)
            x += draw_text(surface, (x, y), title, title_colour)
            draw_text(surface, (x, y), " ]", corner)
        return surface

    def blit(self, screen, topleft, now_ms, dim=0, alpha=255):
        """Draw to the screen with whatever effect is running. `dim` (0-255) darkens a hold;
        `alpha` fades the whole panel."""
        if not self.is_open:
            return
        if alpha < 255:
            self.surface.set_alpha(max(0, alpha))
            self._blit(screen, topleft, now_ms, dim)
            self.surface.set_alpha(None)
            return
        self._blit(screen, topleft, now_ms, dim)

    def _blit(self, screen, topleft, now_ms, dim):
        if self.broken_at is not None:
            self._blit_breaking(screen, topleft, now_ms)
            return
        x, y = topleft
        inner = pygame.Rect(x + CELL_W, y + CELL_H, self.width - 2 * CELL_W, self.height - 2 * CELL_H)
        wipe = (now_ms - self.opened_at) / WIPE_MS
        if wipe < 1:
            shown = max(0, int(self.height * wipe))
            screen.blit(self.surface, topleft, (0, 0, self.width, shown))
            line = pygame.Surface((self.width, WIPE_LINE), pygame.SRCALPHA)
            line.fill((*lift(LABEL, 0.4), WIPE_ALPHA))
            screen.blit(line, (x, y + shown))
            return
        screen.blit(self.surface, topleft)
        if dim:
            veil = pygame.Surface(inner.size, pygame.SRCALPHA)
            veil.fill((*BLACK, dim))
            screen.blit(veil, inner.topleft)
        if now_ms < self.flash_until:
            veil = pygame.Surface(inner.size, pygame.SRCALPHA)
            veil.fill((*self.flash_colour[:3], FLASH_ALPHA))
            screen.blit(veil, inner.topleft)

    def _blit_breaking(self, screen, topleft, now_ms):
        """Cells drop out in a scattered order while the rest sag and fall."""
        progress = min(1.0, (now_ms - self.broken_at) / BREAK_MS)
        x, y = topleft
        for row in range(self.rows):
            for col in range(self.cols):
                hold = _noise(col, row)
                if hold < progress:
                    continue
                fall = int(BREAK_FALL * progress * progress * (1.5 - hold))
                area = (col * CELL_W, row * CELL_H, CELL_W, CELL_H)
                screen.blit(self.surface, (x + col * CELL_W, y + row * CELL_H + fall), area)
