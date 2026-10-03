"""Dune-style personal shield: a blocky blue shell drawn on a coarse grid and scaled up.

Pygame draws it, not glyphs, but the hard 4 px blocks, binary edges and palette blues keep
it in step with the glyph art. Brightness drifts per block and bands crawl down the shell.
"""
import pygame

BLOCK = 4  # screen px per shield block
BLOCKS = 18  # across; 72 px around the 48 px ship
RIM = 0.8  # superellipse radius where the brighter rim starts
STEP_MS = 90  # shimmer changes this often
RIM_COLOR = (0, 150, 255)  # Qud "B"
FILL_COLOR = (0, 72, 189)  # Qud "b"
FLASH_COLOR = (190, 230, 255)
WEAK = 0.25  # below this strength, blocks start dropping out


def _noise(i, j, step):
    h = (i * 73856093) ^ (j * 19349663) ^ (step * 83492791)
    h = ((h ^ (h >> 13)) * 1274126177) & 0xFFFFFFFF
    return ((h ^ (h >> 16)) & 0xFF) / 255.0


def shield_surface(strength, now_ms, flash=False):
    """The shell at `strength` 0..1 (charge times how far it has faded in)."""
    small = pygame.Surface((BLOCKS, BLOCKS), pygame.SRCALPHA)
    step = now_ms // STEP_MS
    for j in range(BLOCKS):
        v = (j + 0.5) / BLOCKS * 2 - 1
        band = (j + step) % 4 == 0
        for i in range(BLOCKS):
            u = (i + 0.5) / BLOCKS * 2 - 1
            r = (u ** 4 + v ** 4) ** 0.25
            if r > 1:
                continue
            n = _noise(i, j, step)
            if strength < WEAK and n < 0.6 * (1 - strength / WEAK):
                continue
            rim = r > RIM
            alpha = (150 if rim else 45) + (25 if band else 0) + int(50 * (n - 0.5))
            alpha = int(alpha * (0.35 + 0.65 * strength))
            if flash:
                color, alpha = FLASH_COLOR, min(255, alpha + 90)
            else:
                color = RIM_COLOR if rim else FILL_COLOR
            small.set_at((i, j), (*color, max(0, min(255, alpha))))
    return pygame.transform.scale(small, (BLOCKS * BLOCK, BLOCKS * BLOCK))


def draw_shield(screen, center, strength, now_ms, flash=False):
    if strength <= 0:
        return
    surface = shield_surface(strength, now_ms, flash)
    screen.blit(surface, surface.get_rect(center=center))
