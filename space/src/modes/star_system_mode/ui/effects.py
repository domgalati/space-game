"""Screen effects: the edges glowing when something hits you, and a small shake.

The vignette glows red on hull damage, orange in solar heat and amber when a ping catches
you. A glow fades over VIGNETTE_MS; heat holds while you're in it. Only hull hits and kills
shake the screen.
"""
import pygame

from .theme import pulse

VIGNETTE_MS = 500
VIGNETTE_DEPTH = 48  # px the glow reaches in from each edge
VIGNETTE_STRENGTH = 120  # alpha at the very edge
HOLD_LEVEL = 0.55  # a held glow (heat) sits at this share, swelling a little on the pulse
SHAKE_MS = 150
SHAKE_PX = 3


class Vignette:
    def __init__(self):
        self.colour = None
        self.started_at = 0
        self._strips = {}

    def glow(self, colour, now_ms):
        self.colour, self.started_at = colour, now_ms

    def level(self, now_ms):
        if self.colour is None:
            return 0.0
        return max(0.0, 1 - (now_ms - self.started_at) / VIGNETTE_MS)

    def draw(self, screen, now_ms, hold=None):
        """`hold` is a colour to keep glowing, like the sun's heat, under any fading glow."""
        level = self.level(now_ms)
        if hold is not None:
            held = HOLD_LEVEL * (0.85 + 0.15 * pulse(now_ms))
            if held > level:
                self._draw(screen, hold, held)
                return
        if level > 0:
            self._draw(screen, self.colour, level)

    def _draw(self, screen, colour, level):
        strips = self._strips.get((colour, screen.get_size()))
        if strips is None:
            strips = self._strips[(colour, screen.get_size())] = _edge_strips(colour, screen.get_size())
        alpha = int(255 * min(1.0, level))
        for surface, position in strips:
            surface.set_alpha(alpha)
            screen.blit(surface, position)


def _edge_strips(colour, size):
    """Four gradient strips, edges in. The corners overlap, so they glow a little more."""
    width, height = size
    depth = VIGNETTE_DEPTH
    ramp = [(*colour[:3], int(VIGNETTE_STRENGTH * (1 - i / depth) ** 2)) for i in range(depth)]
    top = pygame.Surface((width, depth), pygame.SRCALPHA)
    left = pygame.Surface((depth, height), pygame.SRCALPHA)
    for i, tone in enumerate(ramp):
        top.fill(tone, (0, i, width, 1))
        left.fill(tone, (i, 0, 1, height))
    bottom = pygame.transform.flip(top, False, True)
    right = pygame.transform.flip(left, True, False)
    return [(top, (0, 0)), (bottom, (0, height - depth)), (left, (0, 0)), (right, (width - depth, 0))]


class Shake:
    def __init__(self):
        self.until = 0

    def start(self, now_ms):
        self.until = now_ms + SHAKE_MS

    def offset(self, now_ms):
        """(dx, dy) to shift the world by this frame; it jumps every 16 ms while shaking."""
        if now_ms >= self.until:
            return 0, 0
        step = now_ms // 16
        h = ((step * 73856093) ^ (step >> 3) * 19349663) & 0xFFFF
        return h % (2 * SHAKE_PX + 1) - SHAKE_PX, (h >> 8) % (2 * SHAKE_PX + 1) - SHAKE_PX
