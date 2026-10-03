"""Drawing for the sensor game: area-ping rings, bearing wedges and the ships you can sense.

Rings and wedges go on one translucent overlay. Rings are coarse 4 px dots, like the
shield shell, so they sit with the glyph art.
"""
import math

import pygame

from util.config import SCREEN_HEIGHT, SCREEN_WIDTH

from .sensors import PING_RANGE, range_label

OWN = (119, 191, 207)  # Qud "C"
HOSTILE = (233, 159, 16)  # Qud "O"
BLINK = (255, 255, 255)
DOT = 4
DOT_SPACING = 18  # px between ring dots along the circumference
RING_ALPHA = 210
WEDGE_LENGTH = 2400
WEDGE_ALPHA = 24  # faint fill; the dotted edges carry the bearing
EDGE_ALPHA = 170
WEDGE_STEPS = 8
BLINK_PX = 40  # a contact blinks while a ring passes this close to it
EDGE_MARGIN = 28
VESSEL_GLYPH = "<o>"
MARKER_SCALE = 2  # the "?" at a wedge's end is drawn at twice the glyph size


def _to_screen(point, camera):
    return point[0] - camera.x, point[1] - camera.y


def _ring_on_screen(center, radius):
    nearest_x = min(max(center[0], 0), SCREEN_WIDTH)
    nearest_y = min(max(center[1], 0), SCREEN_HEIGHT)
    nearest = math.hypot(center[0] - nearest_x, center[1] - nearest_y)
    farthest = max(math.hypot(center[0] - x, center[1] - y)
                   for x in (0, SCREEN_WIDTH) for y in (0, SCREEN_HEIGHT))
    return nearest - DOT <= radius <= farthest + DOT


def _draw_ring(overlay, center, radius, color, alpha):
    count = max(12, int(2 * math.pi * radius / DOT_SPACING))
    for i in range(count):
        angle = 2 * math.pi * i / count
        x = center[0] + radius * math.cos(angle)
        y = center[1] + radius * math.sin(angle)
        if 0 <= x < SCREEN_WIDTH and 0 <= y < SCREEN_HEIGHT:
            overlay.fill((*color, alpha), (int(x) - DOT // 2, int(y) - DOT // 2, DOT, DOT))


def _wedge_polygon(origin, wedge):
    points = [origin]
    for i in range(WEDGE_STEPS + 1):
        angle = math.radians(wedge.angle - wedge.half_width + 2 * wedge.half_width * i / WEDGE_STEPS)
        points.append((origin[0] + WEDGE_LENGTH * math.cos(angle), origin[1] + WEDGE_LENGTH * math.sin(angle)))
    return points


def _draw_edge(overlay, origin, angle, color, alpha):
    dx, dy = math.cos(math.radians(angle)), math.sin(math.radians(angle))
    for step in range(DOT_SPACING, WEDGE_LENGTH, DOT_SPACING):
        x, y = origin[0] + dx * step, origin[1] + dy * step
        if 0 <= x < SCREEN_WIDTH and 0 <= y < SCREEN_HEIGHT:
            overlay.fill((*color, alpha), (int(x) - DOT // 2, int(y) - DOT // 2, DOT, DOT))


def _last_point_on_screen(origin, angle):
    """Where the wedge's axis leaves the screen, for its "?" marker."""
    last = None
    dx, dy = math.cos(math.radians(angle)), math.sin(math.radians(angle))
    for step in range(0, WEDGE_LENGTH, 40):
        x, y = origin[0] + dx * step, origin[1] + dy * step
        if EDGE_MARGIN <= x <= SCREEN_WIDTH - EDGE_MARGIN and EDGE_MARGIN <= y <= SCREEN_HEIGHT - EDGE_MARGIN:
            last = (x, y)
    return last


def draw_sensor_overlay(screen, camera, sensors, now_turn, now_ms, font, ring_turn=None):
    """`ring_turn` is a smoothed clock for drawing enemy rings between turns."""
    ring_turn = now_turn if ring_turn is None else ring_turn
    overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
    markers = []
    for wedge in sensors.wedges:
        strength = wedge.strength(now_turn)
        if strength <= 0:
            continue
        color = HOSTILE if wedge.hostile else OWN
        origin = _to_screen(wedge.origin, camera)
        pygame.draw.polygon(overlay, (*color, int(WEDGE_ALPHA * strength)), _wedge_polygon(origin, wedge))
        for side in (-1, 1):
            _draw_edge(overlay, origin, wedge.angle + side * wedge.half_width, color, int(EDGE_ALPHA * strength))
        point = _last_point_on_screen(origin, wedge.angle)
        if point:
            markers.append((point, color, strength, wedge.distance))
    for ring in sensors.rings:
        radius = ring.radius(now_ms, ring_turn)
        center = _to_screen(ring.origin, camera)
        if radius <= 0 or not _ring_on_screen(center, radius):
            continue
        alpha = int(RING_ALPHA * (1 - radius / PING_RANGE))
        _draw_ring(overlay, center, radius, HOSTILE if ring.hostile else OWN, alpha)
    screen.blit(overlay, (0, 0))
    for point, color, strength, distance in markers:
        alpha = int(255 * max(0.35, strength))
        label = font.render("?", True, color)
        label = pygame.transform.scale(label, (label.get_width() * MARKER_SCALE, label.get_height() * MARKER_SCALE))
        label.set_alpha(alpha)
        rect = label.get_rect(center=point)
        screen.blit(label, rect)
        reading = font.render(range_label(distance), True, color)
        reading.set_alpha(alpha)
        spot = reading.get_rect(midtop=(rect.centerx, rect.bottom))
        screen.blit(reading, spot.clamp(screen.get_rect()))


def _blinking(position, rings, now_ms, ring_turn):
    return any(abs(math.dist(ring.origin, position) - ring.radius(now_ms, ring_turn)) < BLINK_PX for ring in rings)


def draw_contacts(screen, camera, vessels, rings, now_ms, font, ring_turn=0):
    """Ships you can sense: their sprite (or a glyph) on screen, an edge marker when off it."""
    screen_rect = screen.get_rect()
    half_w = SCREEN_WIDTH / 2 - EDGE_MARGIN
    half_h = SCREEN_HEIGHT / 2 - EDGE_MARGIN
    center_x, center_y = SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2
    for vessel in vessels:
        colour = getattr(vessel, "colour", HOSTILE)
        color = BLINK if _blinking(vessel.position, rings, now_ms, ring_turn) else colour
        sx, sy = _to_screen(vessel.position, camera)
        if screen_rect.collidepoint(sx, sy):
            if hasattr(vessel, "draw"):
                vessel.draw(screen, (sx, sy), now_ms)
                continue
            glyph = font.render(VESSEL_GLYPH, True, color)
            screen.blit(glyph, glyph.get_rect(center=(sx, sy)))
            continue
        dx, dy = sx - center_x, sy - center_y
        scale = min(half_w / abs(dx) if dx else math.inf, half_h / abs(dy) if dy else math.inf)
        mx, my = center_x + dx * scale, center_y + dy * scale
        angle = math.atan2(dy, dx)
        tip = (mx + math.cos(angle) * 10, my + math.sin(angle) * 10)
        left = (mx + math.cos(angle + 2.5) * 8, my + math.sin(angle + 2.5) * 8)
        right = (mx + math.cos(angle - 2.5) * 8, my + math.sin(angle - 2.5) * 8)
        pygame.draw.polygon(screen, color, [tip, left, right])
