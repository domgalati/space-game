"""The look of space mode's HUD: Qud palette, TeleSys on its 8x16 grid, and shared timers.

Every blink, pulse and flash reads the same clock, so everything on screen blinks in step.
"""
import math

import pygame

from util.config import resolve_game_path

from world.factions import FACTIONS as FACTION_INFO


def _hex(code):
    return tuple(int(code[i:i + 2], 16) for i in (1, 3, 5))


# Caves of Qud colours, as in tools/art/qud_glyph and the glyph-art sprites.
QUD = {key: _hex(code) for key, code in {
    "k": "#0f3b3a", "K": "#155352", "y": "#b1c9c3", "Y": "#ffffff",
    "r": "#a64a2e", "R": "#d74200", "o": "#f15f22", "O": "#e99f10",
    "w": "#98875f", "W": "#cfc041", "g": "#009403", "G": "#00c420",
    "b": "#0048bd", "B": "#0096ff", "c": "#40a4b9", "C": "#77bfcf",
    "m": "#b154cf", "M": "#da5bd6",
}.items()}

LABEL = QUD["C"]  # row labels and panel titles
VALUE = QUD["y"]
BRIGHT = QUD["Y"]
SHIELD = QUD["B"]
SHIELD_LOW = QUD["b"]  # a lowered shield
WEAPON = QUD["C"]
GOOD = QUD["G"]
WARN = QUD["O"]
DANGER = QUD["R"]
HEAT = QUD["o"]
PATROL = QUD["G"]
DIM = QUD["k"]
FILL = (6, 16, 15, 228)  # Qud "night", translucent so planets show through a little
BLACK = (0, 0, 0)
FACTIONS = {faction: info["colour"] for faction, info in FACTION_INFO.items() if "colour" in info}

CELL_W, CELL_H = 8, 16  # TeleSys at its native 16 px
FONT_PATH = "space/assets/fonts/TeleSys.ttf"
FONT_SIZE = 16

PULSE_MS = 1200  # brightness swells and falls once per cycle
PULSE_STEPS = 8  # pulses step in brightness, like the glyph art, and keep the text cache small
PULSE_LOW = 0.45  # a pulse's dimmest point, as a share of full brightness
BLINK_MS = 250  # 2 Hz: on for this long, then off for this long
FLASH_MS = 150
COUNT_MS = 240  # a dropping value counts down over this long
WIPE_MS = 200  # a panel's scanline wipe as it opens

_font = None


def font():
    """TeleSys at 16 px. Loaded on first use, once pygame's font module is up."""
    global _font
    if _font is None:
        if not pygame.font.get_init():
            pygame.font.init()
        _font = pygame.font.Font(resolve_game_path(FONT_PATH), FONT_SIZE)
    return _font


def mix(colour, target, amount):
    return tuple(int(round(c + (t - c) * amount)) for c, t in zip(colour[:3], target[:3]))


# Panel borders: dark teal, lifted toward "c" so the thin dash glyphs hold up over a planet.
FRAME = mix(QUD["K"], QUD["c"], 0.45)


def shade(colour, amount):
    """Darker by `amount` (0 keeps it, 1 is black)."""
    return mix(colour, BLACK, amount)


def lift(colour, amount):
    """Lighter by `amount` (0 keeps it, 1 is white)."""
    return mix(colour, BRIGHT, amount)


def pulse(now_ms):
    """0 to 1 and back over PULSE_MS, in PULSE_STEPS steps."""
    wave = 0.5 - 0.5 * math.cos(2 * math.pi * (now_ms % PULSE_MS) / PULSE_MS)
    return round(wave * PULSE_STEPS) / PULSE_STEPS


def pulsing(colour, now_ms, low=PULSE_LOW):
    """`colour` swelling between `low` and full brightness on the shared pulse."""
    return shade(colour, (1 - low) * (1 - pulse(now_ms)))


def blink(now_ms):
    """True for the on half of the shared 2 Hz blink."""
    return (now_ms // BLINK_MS) % 2 == 0
