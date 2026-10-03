"""Glyph drawing for the HUD: text with glow, block bars, chips, keycaps and scrambled readings.

Everything is TeleSys on its 8x16 cell. Positions are pixels; widths come back in pixels so
callers can lay pieces out left to right.
"""
import pygame

from .theme import CELL_H, CELL_W, FILL, VALUE, blink, font, pulsing, shade

FULL, HEAVY, LIGHT, TRACK = "█", "▓", "▒", "░"  # █ ▓ ▒ ░
TRACK_SHADE = 0.62  # a bar's empty track is its fill colour this much darker
BAR_TOP, BAR_HEIGHT = 3, 10  # px of the cell a bar keeps: TeleSys cap height
GLOW_SHADE = 0.55  # the halo behind glowing text
CHIP_BRACKET_SHADE = 0.45
BLINK_OFF_SHADE = 0.7  # a blinking chip's off phase: dimmed, so the row doesn't jump
SCRAMBLE = "?#:%&!*;"
SCRAMBLE_MS = 110  # scrambled readings change this often
CACHE_LIMIT = 2048

_cache = {}


def render(text, colour, scale=1):
    """`text` in TeleSys, cached. Scale 2 is for banners: nearest-neighbour, so pixels stay hard."""
    key = (text, tuple(colour[:3]), scale)
    surface = _cache.get(key)
    if surface is None:
        if len(_cache) >= CACHE_LIMIT:
            _cache.clear()
        surface = font().render(text, False, colour[:3])
        if scale != 1:
            surface = pygame.transform.scale(surface, (surface.get_width() * scale, surface.get_height() * scale))
        _cache[key] = surface
    return surface


def text_width(text, scale=1):
    return len(text) * CELL_W * scale


def draw_text(surface, pos, text, colour, scale=1, glow=False):
    """Returns the width drawn. A glow is the text again in a darker shade, a pixel out each way."""
    if not text:
        return 0
    x, y = pos
    if glow:
        halo = render(text, shade(colour, GLOW_SHADE), scale)
        for dx, dy in ((-scale, 0), (scale, 0), (0, -scale), (0, scale)):
            surface.blit(halo, (x + dx, y + dy))
    surface.blit(render(text, colour, scale), (x, y))
    return text_width(text, scale)


def bar_glyphs(fraction, cells):
    """(fill, edge, track) strings for a bar `fraction` full: solid cells, a shaded edge on a
    part-filled cell (▓ half or more, ▒ less), then track. Anything above zero shows."""
    fraction = max(0.0, min(1.0, fraction))
    quarters = round(fraction * cells * 4)
    if fraction > 0 and quarters == 0:
        quarters = 1
    full, rest = divmod(quarters, 4)
    edge = HEAVY if rest >= 2 else LIGHT if rest else ""
    return FULL * full, edge, TRACK * (cells - full - len(edge))


def draw_bar(surface, pos, cells, fraction, colour, track=None):
    """A block-glyph bar. The track defaults to a darker shade of the fill. Returns the width.

    Block glyphs fill the whole cell, so bars are trimmed to cap height to keep a gap
    between bars on neighbouring rows."""
    fill, edge, empty = bar_glyphs(fraction, cells)
    x, y = pos
    for text, tone in ((fill + edge, colour), (empty, track or shade(colour, TRACK_SHADE))):
        if text:
            glyphs = render(text, tone)
            surface.blit(glyphs, (x, y + BAR_TOP), (0, BAR_TOP, glyphs.get_width(), BAR_HEIGHT))
            x += glyphs.get_width()
    return cells * CELL_W


def effect(colour, kind, now_ms):
    """`colour` as it shows this frame for a "pulse" or "blink" effect (None for steady)."""
    if kind == "pulse":
        return pulsing(colour, now_ms)
    if kind == "blink" and not blink(now_ms):
        return shade(colour, BLINK_OFF_SHADE)
    return colour


def draw_chip(surface, pos, label, colour):
    """A bracketed status tag, `[GLARE]`. Returns the width."""
    x, y = pos
    bracket = shade(colour, CHIP_BRACKET_SHADE)
    x += draw_text(surface, (x, y), "[", bracket)
    x += draw_text(surface, (x, y), label, colour)
    draw_text(surface, (x, y), "]", bracket)
    return text_width(label) + 2 * CELL_W


def key_width(label):
    return text_width(label) + 2 * CELL_W


def draw_key(surface, pos, label, colour, now_ms, lit=True, pulse=False):
    """A little keycap, as wide as `[label]`: lit, lit and pulsing, or dark. Returns the width."""
    x, y = pos
    width = key_width(label)
    face = pygame.Rect(x + 1, y + 1, width - 2, CELL_H - 3)
    if lit:
        face_colour = pulsing(colour, now_ms) if pulse else colour
        lip, letter = shade(colour, 0.55), FILL[:3]
    else:
        face_colour, lip, letter = shade(colour, 0.78), shade(colour, 0.88), shade(VALUE, 0.35)
    pygame.draw.rect(surface, lip, face.move(0, 2), border_radius=2)
    pygame.draw.rect(surface, face_colour, face, border_radius=2)
    draw_text(surface, (x + CELL_W, y), label, letter)
    return width


def scramble(length, now_ms, salt=0):
    """Noise glyphs for a reading you haven't scanned yet. They change every SCRAMBLE_MS."""
    step = now_ms // SCRAMBLE_MS
    chars = []
    for i in range(length):
        h = (i * 73856093) ^ (step * 19349663) ^ (salt * 83492791)
        h = ((h ^ (h >> 13)) * 1274126177) & 0xFFFFFFFF
        chars.append(SCRAMBLE[(h ^ (h >> 16)) % len(SCRAMBLE)])
    return "".join(chars)
