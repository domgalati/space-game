"""Procedural ASCII imaging for the ship-computer scan panel."""

import math
import random
import zlib

import pygame

from entities.planet import Planet

ART_COLS = 38
ART_ROWS = 13
PLANET_RADIUS_ROWS = 5.8
RING_SCALE_X = 1.38
RING_SCALE_Y = 0.30

DIM = (28, 84, 52)
MID = (46, 139, 87)
BRIGHT = (140, 240, 160)
ICE = (215, 255, 235)
OCEAN_DIM = (22, 60, 78)
OCEAN_MID = (40, 115, 140)
OCEAN_BRIGHT = (95, 190, 210)
CITY_LIGHTS = (225, 255, 205)
LAVA = (255, 170, 60)
LAVA_DIM = (190, 90, 30)
LAVA_HAZE = (130, 70, 35)

_LIGHT = (-0.55, -0.45, 0.70)
_LIGHT_LEN = math.sqrt(sum(v * v for v in _LIGHT))
LIGHT_DIR = tuple(v / _LIGHT_LEN for v in _LIGHT)

# Fraction of the visible disk above LAND_THRESHOLD (land, or crust away from fissures).
LAND_SHARE = {"Terran": 0.45, "Suburban": 0.7, "Urban": 0.8, "Industrial": 0.5}
LAND_THRESHOLD = {"Terran": 0.0, "Suburban": -0.4, "Urban": -0.45, "Industrial": 0.0}

SHADE_RAMP = " .:-=+*#%@"
OCEAN_RAMP = " .,-~~"
FIELD_CHARS = "\",;:'"

STATION_ART = [
    " [#][#][#]     |     [#][#][#] ",
    " [#][#][#] .---+---. [#][#][#] ",
    "    |     /  .---.  \\     |    ",
    " ===+====|  | o o |  |====+=== ",
    "    |     \\  '---'  /     |    ",
    " [#][#][#] '---+---' [#][#][#] ",
    " [#][#][#]     |     [#][#][#] ",
]
STATION_COLORS = {"#": DIM, "o": CITY_LIGHTS, "=": BRIGHT, "+": BRIGHT}
WRECK_ART = [
    "      .     *        '    ",
    "   __/\\_     .  /|        ",
    "  [#]  \\'--.   /=|  .    ",
    "   '  *  |#|  '  |_\\      ",
    "    .   /==/   *     [#]  ",
    "  *   '--'  .    '   ' .  ",
]
WRECK_COLORS = {"#": DIM, "*": LAVA, "=": BRIGHT}


def _seed_for(name):
    return zlib.crc32(name.encode("utf-8"))


def _make_noise(seed):
    rng = random.Random(seed)
    terms = []
    for i in range(6):
        vx, vy, vz = (rng.gauss(0, 1) for _ in range(3))
        length = math.sqrt(vx * vx + vy * vy + vz * vz) or 1.0
        frequency = rng.uniform(1.6, 2.6) * (1 + i * 0.6)
        amplitude = 1 / (1 + i * 1.2)
        terms.append((vx / length * frequency, vy / length * frequency, vz / length * frequency,
                      rng.uniform(0, 2 * math.pi), amplitude))
    total = sum(t[4] for t in terms)

    def noise(x, y, z):
        value = sum(a * math.sin(kx * x + ky * y + kz * z + phase) for kx, ky, kz, phase, a in terms)
        return 1.6 * value / total

    return noise


def _ramp(chars, level):
    level = min(max(level, 0.0), 0.999)
    return chars[int(level * len(chars))]


def _background_star(col, row, seed):
    h = (col * 73856093) ^ (row * 19349663) ^ seed
    if h % 89 == 0:
        return ".", DIM
    if h % 233 == 0:
        return "+", MID
    return " ", DIM


def _tone(level, dim, mid, bright):
    return bright if level > 0.6 else mid if level > 0.3 else dim


def _ocean(light):
    level = max(light, 0.0) * 0.65
    return _ramp(OCEAN_RAMP, level), _tone(level + 0.1, OCEAN_DIM, OCEAN_MID, OCEAN_BRIGHT)


def _land(light, relief):
    """Land density: brighter where lit, denser where the terrain is higher."""
    level = max(light, 0.0) * (0.9 + 0.3 * min(relief, 1.0))
    return _ramp(SHADE_RAMP, level), _tone(level, DIM, MID, BRIGHT)


def _planet_cell(planet_type, light, tex, ny, col, row):
    """Surface character and color for one cell on the sphere."""
    if planet_type == "Industrial":
        if abs(tex) < 0.09:
            hot = abs(tex) < 0.045
            return ("*" if hot else "="), (LAVA if hot else LAVA_DIM)
        level = max(light, 0.0) * 0.9
        return _ramp(SHADE_RAMP, level), _tone(level, DIM, MID, BRIGHT)

    if planet_type == "Urban":
        if tex < -0.45:
            return _ocean(light)
        if light < 0.12:
            if (col * 7 + row * 13) % 4 == 0:
                return ("o" if (col + row) % 3 == 0 else ":"), CITY_LIGHTS
            return " ", DIM
        street = col % 4 == 0 or row % 3 == 0
        level = light * (0.7 if street else 1.0)
        char = ("+" if col % 4 == 0 and row % 3 == 0 else "-" if row % 3 == 0 else "|") if street else "#"
        if level < 0.3:
            char = "." if street else ":"
        return char, _tone(level, DIM, MID, BRIGHT)

    if planet_type == "Suburban":
        if tex < -0.4:
            return _ocean(light)
        if light < 0.12:
            return " ", DIM
        if (col * 5 + row * 3) % 13 == 0 and light > 0.3:
            return "^", ICE
        band = int((tex + 1.0) * 4) % len(FIELD_CHARS)
        char = FIELD_CHARS[band] if light > 0.3 else "."
        return char, _tone(light, DIM, MID, BRIGHT)

    if planet_type == "Terran":
        if abs(ny) > 0.82:
            level = max(light, 0.0)
            return _ramp(SHADE_RAMP, min(level * 1.2, 0.99)), (ICE if level > 0.3 else DIM)
        if tex > 0.0:
            return _land(light, tex * 2)
        return _ocean(light)

    level = max(light, 0.0)
    return _ramp(SHADE_RAMP, level), _tone(level, DIM, MID, BRIGHT)


def planet_cells(planet, char_aspect):
    """Grid of (char, color) cells: a lit sphere with type-specific surface features."""
    seed = _seed_for(planet.name)
    noise = _make_noise(seed)
    radius_y = PLANET_RADIUS_ROWS
    radius_x = PLANET_RADIUS_ROWS * char_aspect
    center_x, center_y = ART_COLS / 2, ART_ROWS / 2
    has_ring = planet.planet_type == "Urban"
    has_atmosphere = planet.planet_type in ("Terran", "Suburban", "Urban")

    # Re-center the noise on the visible disk so each type gets its intended land share.
    samples = []
    for row in range(ART_ROWS):
        for col in range(ART_COLS):
            nx = (col + 0.5 - center_x) / radius_x
            ny = (row + 0.5 - center_y) / radius_y
            d2 = nx * nx + ny * ny
            if d2 <= 1.0:
                samples.append(noise(nx, ny, math.sqrt(1.0 - d2)))
    samples.sort()
    sea_share = 1.0 - LAND_SHARE.get(planet.planet_type, 0.5)
    offset = samples[int(sea_share * (len(samples) - 1))] - LAND_THRESHOLD.get(planet.planet_type, 0.0)

    grid = []
    for row in range(ART_ROWS):
        line = []
        for col in range(ART_COLS):
            dx = col + 0.5 - center_x
            dy = row + 0.5 - center_y
            nx, ny = dx / radius_x, dy / radius_y
            d2 = nx * nx + ny * ny

            ring = None
            if has_ring:
                ex = dx / (radius_x * RING_SCALE_X)
                ey = dy / (radius_y * RING_SCALE_Y)
                if 0.72 < ex * ex + ey * ey < 1.0:
                    ring = ("=", BRIGHT) if dy > 0 else ("-", MID)

            if d2 <= 1.0:
                if ring and dy > 0:
                    line.append(ring)
                    continue
                nz = math.sqrt(1.0 - d2)
                light = nx * LIGHT_DIR[0] + ny * LIGHT_DIR[1] + nz * LIGHT_DIR[2]
                tex = noise(nx, ny, nz) - offset
                line.append(_planet_cell(planet.planet_type, light, tex, ny, col, row))
            elif ring:
                line.append(ring)
            elif d2 <= 1.18 and nx * LIGHT_DIR[0] + ny * LIGHT_DIR[1] > 0.1:
                if has_atmosphere:
                    line.append((".", DIM))
                elif planet.planet_type == "Industrial":
                    line.append((":", LAVA_HAZE))
                else:
                    line.append((" ", DIM))
            else:
                line.append(_background_star(col, row, seed))
        grid.append(line)
    return grid


def station_cells(art=STATION_ART, colors=STATION_COLORS, seed_name="station"):
    seed = _seed_for(seed_name)
    top = (ART_ROWS - len(art)) // 2
    left = (ART_COLS - len(art[0])) // 2
    grid = []
    for row in range(ART_ROWS):
        line = []
        for col in range(ART_COLS):
            art_row, art_col = row - top, col - left
            char = " "
            if 0 <= art_row < len(art) and 0 <= art_col < len(art[art_row]):
                char = art[art_row][art_col]
            if char == " ":
                line.append(_background_star(col, row, seed))
            else:
                line.append((char, colors.get(char, MID)))
        grid.append(line)
    return grid


def render_scan_art(target, font):
    """Pre-render the imaging art for a scan target to a surface (None for no target)."""
    if target is None:
        return None
    char_width = font.size("M")[0]
    line_height = font.get_linesize()
    if isinstance(target, Planet):
        cells = planet_cells(target, line_height / char_width)
    elif getattr(target, "obj_type", None) == "Wreck":
        cells = station_cells(WRECK_ART, WRECK_COLORS, "wreck")
    else:
        cells = station_cells()

    surface = pygame.Surface((ART_COLS * char_width, ART_ROWS * line_height), pygame.SRCALPHA)
    glyphs = {}
    for row, line in enumerate(cells):
        for col, (char, color) in enumerate(line):
            if char == " ":
                continue
            glyph = glyphs.get((char, color))
            if glyph is None:
                glyph = glyphs[(char, color)] = font.render(char, True, color)
            surface.blit(glyph, (col * char_width, row * line_height))
    return surface


def caption_for(target):
    if isinstance(target, Planet):
        return f"{target.planet_type.upper()} // {target.planet_guild.upper()}"
    return target.obj_type.upper()
