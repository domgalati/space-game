"""Capitol station (Nexum Astra) drawn entirely with the 8x16 TeleSys GlyphCanvas.

288x144 cells = 2304x2304 px, the same size as a flight planet. Every visible cell is
one printable ASCII glyph on an optional solid background. Shapes are computed per
cell from simple geometry (spheres for the domes, a cylinder for the drum, an ellipse
band for the ring) and lit from the upper left like the planet disks.

Run with the same numpy/Pillow environment as ../generate_samples.py.
Writes the station PNG, the literal glyph grid (station.txt) and validation.json.
"""
from pathlib import Path
import importlib.util
import json
import math

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[3]
spec = importlib.util.spec_from_file_location("sample_art", ROOT.parent / "generate_samples.py")
art = importlib.util.module_from_spec(spec)
spec.loader.exec_module(art)

CW, CH = art.CELL_W, art.CELL_H
COLS, ROWS = 288, 144
SIZE = COLS * CW
AXIS = SIZE / 2
Q = art.QUD
LIGHT = art.LIGHT
canvas = art.GlyphCanvas(COLS, ROWS)

# Hull backgrounds from shadow to lit, so large surfaces keep their volume at 1:1.
HULL = ["#040b0a", "#0b1a19", "#0f2423", "#143130"]
GLASS = art.QUD_BG["glass"]
VOID = art.QUD_BG["void"]
RAMP = ["k", "K", "c", "C", "y", "Y"]
MIRROR = str.maketrans("/\\()[]<>", "\\/)(][><")

# Layout in pixels. Rows are 16 px, so horizontal bands are given as row ranges.
DOME_R, DOME_Y = 560, 992              # main dome sphere: center on the attic
DRUM_R = 600                           # colonnade cylinder under the cornice
RING_Y, RING_A, RING_B = 1180, 1040, 470
RING_W, RING_T = 84, 44                # deck width at the ends, outer wall height
WING_NEAR, WING_FAR = 584, 896         # wing facade, as offsets from the axis
MAST_OFFSET = 696
DOCK_R, DOCK_Y = 320, 1824             # south dome over the bay
BAY = (904, 1840, 1400, 2000)          # mouth x0, y0, x1, y1
STACKS = ((808, 89, 117), (640, 89, 128), (440, 93, 135))  # offset, first row, last row


def put(col, row, char, color, bg=None):
    assert len(char) == 1 and 32 <= ord(char) <= 126, char
    canvas.set(col, row, char, Q[color], bg)


def fg(level):
    return RAMP[min(max(int(level * len(RAMP)), 0), len(RAMP) - 1)]


def hull(level):
    return HULL[min(max(int(level * len(HULL)), 0), len(HULL) - 1)]


def shade(nx, ny, nz):
    """0..1 light for a screen-space normal (y down), the same light as the planets.

    Squared so only the upper-left really shines; a raw dot product lights most of a dome.
    """
    return 0.06 + 0.94 * max(0.0, nx * LIGHT[0] + ny * LIGHT[1] + nz * LIGHT[2]) ** 2


def hsh(col, row, salt=0):
    return art._cell_hash(col, row, salt)


def cells(x0, y0, x1, y1):
    """Cells whose centers fall inside the pixel box, with those centers."""
    for row in range(max(0, int(y0 // CH)), min(ROWS, int(y1 // CH) + 1)):
        y = row * CH + CH / 2
        if not y0 <= y < y1:
            continue
        for col in range(max(0, int(x0 // CW)), min(COLS, int(x1 // CW) + 1)):
            x = col * CW + CW / 2
            if x0 <= x < x1:
                yield col, row, x, y


def stroke(dx, dy, flat="-"):
    """Glyph that follows a pixel-space direction on 8x16 cells."""
    angle = math.degrees(math.atan2(-dy, dx)) % 180
    if angle < 20 or angle >= 160:
        return flat
    if angle < 70:
        return "/"
    if angle < 110:
        return "|"
    return "\\"


def col_at(offset, side):
    """Cell column for a pixel offset from the axis on one side (-1 left, 1 right)."""
    return int((AXIS + side * offset) // CW)


def side_put(side, col, row, char, color, bg=None):
    put(col, row, char.translate(MIRROR) if side > 0 else char, color, bg)


def band(row, offset, left, fill, right, level_at, bg_at=None):
    """One row spanning +-offset px: end caps and a fill glyph, lit across x."""
    c0, c1 = col_at(offset, -1), col_at(offset, 1)
    for col in range(c0, c1 + 1):
        x = col * CW + CW / 2
        level = level_at((x - AXIS) / offset)
        char = left if col == c0 else right if col == c1 else fill(col) if callable(fill) else fill
        put(col, row, char, fg(level), bg_at(level) if bg_at else hull(level * 0.7))


def facade_light(u):
    """Flat front faces: lit side on the left, a little darker to the right."""
    return 0.62 - 0.22 * u


# ---------------------------------------------------------------- ring

def ring(front):
    """Habitat ring: a flat deck seen from above, outer wall on the near half."""
    a, b = RING_A, RING_B
    inner = 1 - RING_W / a  # the inner edge is the same ellipse scaled down
    ai, bi = a * inner, b * inner
    for col, row, x, y in cells(AXIS - a - 8, RING_Y - b - 8, AXIS + a + 8, RING_Y + b + RING_T + 8):
        dx, dy = x - AXIS, y - RING_Y
        if (dy >= 0) != front:
            continue
        eo = (dx / a) ** 2 + (dy / b) ** 2
        ei = (dx / ai) ** 2 + (dy / bi) ** 2
        t = math.atan2(dy / b, dx / a)
        speed = math.hypot(a * math.sin(t), b * math.cos(t))
        joint = abs((math.degrees(t) + 3) % 6 - 3) * math.pi / 180 * speed < 5
        u = dx / a
        h = hsh(col, row, 3)
        if eo <= 1 and ei >= 1:
            # Rails on both edges follow the curve; seams cross the deck at each joint.
            rho = math.sqrt(eo)
            cell = (abs(dx) / (a * a) * CW + abs(dy) / (b * b) * CH) / max(rho, 1e-6)
            level = (0.66 - 0.24 * u) * (1.0 if front else 0.62)
            tangent = stroke(-a * math.sin(t), b * math.cos(t), "=")
            if rho > 1 - cell:
                put(col, row, tangent, fg(level + 0.15), hull(level * 0.55))
            elif rho < inner + cell:
                put(col, row, tangent, fg(level - 0.1), hull(level * 0.45))
            elif joint:
                put(col, row, stroke(dx / (a * a), dy / (b * b)), fg(level + 0.05), hull(level * 0.5))
            else:
                put(col, row, "o" if h % 17 == 0 else ":" if (col + row) % 2 else ".",
                    fg(level - 0.15), hull(level * 0.5))
        elif front and eo > 1 and (dx / a) ** 2 + ((dy - RING_T) / b) ** 2 <= 1:
            top = b * math.sqrt(max(0.0, 1 - u * u))
            depth = (dy - top) / RING_T
            level = 0.5 - 0.3 * u
            if joint:
                char = "|"
            elif depth < 0.34:
                char = "-"
            elif depth < 0.7:
                char = "o" if col % 3 == 0 else "."
                if char == "o" and h % 11 == 0:
                    put(col, row, char, "O", HULL[0])
                    continue
            else:
                char = "'" if col % 2 else "-"
            put(col, row, char, fg(level), HULL[0])
        elif not front and ei < 1 and (dx / ai) ** 2 + ((dy - RING_T) / bi) ** 2 >= 1:
            put(col, row, ":" if (col + row) % 3 == 0 else ".", "k", HULL[0])


# ---------------------------------------------------------------- masts

def mast(side):
    deck = RING_Y - RING_B * math.sqrt(1 - (MAST_OFFSET / RING_A) ** 2)
    base_row = int(deck // CH) + 1
    top_row = 26
    mc = col_at(MAST_OFFSET, side)
    span = base_row - top_row
    last = None
    for row in range(top_row, base_row + 1):
        half = 1 + round(2 * (row - top_row) / span)
        for col in range(mc - half, mc + half + 1):
            if abs(col - mc) == half:
                char = "|" if last == half else ("/" if col < mc else "\\")
                put(col, row, char, "C" if col < mc else "c")
            elif (row - top_row) % 4 == 0:
                put(col, row, "-", "K")
            elif half >= 2:
                put(col, row, "X" if (col - mc + row) % 2 == 0 else ":", "K")
            else:
                put(col, row, ":", "K")
        last = half
    # Platform, a yardarm with amber running lights, and the green beacon on the antenna.
    for col in range(mc - 3, mc + 4):
        put(col, top_row - 1, "=", "y")
    yard = top_row - 4
    for dc in range(-5, 6):
        put(mc + dc, yard, "o" if abs(dc) == 5 else "+" if dc == 0 else "-", "O" if abs(dc) == 5 else "C")
    for row in range(top_row - 7, top_row - 1):
        if row != yard:
            put(mc, row, "|", "c")
    put(mc, top_row - 8, "*", "G")
    for dc, dr, char in ((-1, 0, "."), (1, 0, "."), (0, -1, "'")):
        put(mc + dc, top_row - 8 + dr, char, "g")


# ---------------------------------------------------------------- wings

WING_TOP = 70  # entablature row; the wings sit lower than the drum so they read as annexes


def wing(side):
    near, far = WING_NEAR, WING_FAR
    mid = (near + far) / 2
    top = WING_TOP
    apex_y, base_y = (top - 8) * CH, (top - 1) * CH + CH / 2

    def lit(offset):
        u = (AXIS + side * offset - AXIS) / far
        return facade_light(u)

    # Roof band behind the pediment.
    for row in range(top - 4, top):
        for off in range(near, far, CW):
            col = col_at(off, side)
            level = lit(off) * 0.7
            put(col, row, "=" if row % 2 else "-", fg(level), hull(level * 0.6))
    # Pediment: a stepped gable with a sealed emblem in the tympanum.
    for row in range(int(apex_y // CH), int(base_y // CH) + 1):
        y = row * CH + CH / 2
        t = min(max((y - apex_y) / (base_y - apex_y), 0.0), 1.0)
        half = (far - near) / 2 * t + 8
        c_out, c_in = col_at(mid + half, side), col_at(mid - half, side)
        lo, hi = sorted((c_out, c_in))
        for col in range(lo, hi + 1):
            off = abs(col * CW + CW / 2 - AXIS)
            level = lit(off)
            if col == lo:
                put(col, row, "/", fg(level + 0.15), hull(level * 0.5))
            elif col == hi:
                put(col, row, "\\", fg(level - 0.1), hull(level * 0.5))
            else:
                put(col, row, "." if hsh(col, row) % 3 else ":", "K", hull(level * 0.5))
    emblem_row = int(base_y // CH) - 2
    mc = col_at(mid, side)
    for dc, char, color in ((-1, "(", "C"), (0, "*", "W"), (1, ")", "C")):
        put(mc + dc, emblem_row, char, color, HULL[1])
    # Entablature, colonnade, base and underside steps.
    lo, hi = sorted((col_at(near, side), col_at(far, side)))
    outer = hi if side > 0 else lo
    columns = [col_at(off, side) for off in range(near + 16, far, 40)]
    base = top + 17
    for row in range(top, base + 5):
        for col in range(lo, hi + 1):
            off = abs(col * CW + CW / 2 - AXIS)
            level = lit(off)
            in_column = any(col in (c, c + side) for c in columns)
            left_edge = any(col == min(c, c + side) for c in columns)
            if col == outer and row <= base:
                char = "+" if row in (top, base) else "|"
                side_put(side, col, row, char, fg(level), hull(level * 0.6))
            elif row == top:
                put(col, row, "=", fg(level + 0.1), hull(level * 0.6))
            elif row == top + 1:
                put(col, row, "|" if col % 4 == 0 else ":", fg(level - 0.1), hull(level * 0.5))
            elif row == top + 2:
                put(col, row, "-", fg(level), hull(level * 0.6))
            elif row < base:
                if in_column:
                    char = "H" if row == top + 3 else "=" if row == base - 1 else "|"
                    put(col, row, char, fg(level + (0.15 if left_edge else -0.1)), hull(level * 0.75))
                elif row in (top + 3, base - 1):
                    put(col, row, "_", fg(level - 0.2), hull(level * 0.4))
                elif row == top + 4:
                    put(col, row, "^", "C", HULL[0])
                elif top + 5 <= row <= base - 3:
                    mullion = (col - columns[0]) % 5 == (2 if side < 0 else 3)
                    put(col, row, "|" if mullion else "-" if row == top + 9 else " ", "c", GLASS)
                else:
                    put(col, row, " ", "K", HULL[0])
            elif row == base:
                put(col, row, "=", fg(level), hull(level * 0.6))
            else:
                # Underside tapers in two steps toward the axis.
                inset = 2 if row <= base + 2 else 5
                if (side < 0 and col < lo + inset) or (side > 0 and col > hi - inset):
                    continue
                edge = col == (lo + inset if side < 0 else hi - inset)
                char = ("'" if edge else "-:"[(col // 3) % 2]) if row % 2 else "="
                put(col, row, char, fg(level - 0.15), hull(level * 0.4))


# ---------------------------------------------------------------- rotunda

def dome(cx, cy, r, rib_deg, bands, windows=False, crown=74):
    """Front-on hemisphere: meridian ribs, latitude bands, lit plates and a hard silhouette."""
    rib = math.radians(rib_deg)
    band_ys = [cy - r * math.sin(math.radians(b)) for b in bands]
    window_y = cy - r * math.sin(math.radians(bands[0] / 2)) if bands else None
    plates = " .:-="  # "#" is kept for the highlight so the lit side does not turn solid
    for col, row, x, y in cells(cx - r, cy - r, cx + r, cy):
        u, v = (x - cx) / r, (cy - y) / r
        d2 = u * u + v * v
        if d2 > 1:
            continue
        nz = math.sqrt(1 - d2)
        level = shade(u, -v, nz)
        lat, lon = math.asin(min(v, 1.0)), math.atan2(u, nz)
        k = round(lon / rib)
        rib_px = r * math.cos(lat) * abs(math.sin(lon) - math.sin(k * rib))
        on_rib = rib_px < CW / 2 and math.degrees(lat) < crown
        on_band = any(abs(y - by) < CH / 2 for by in band_ys)
        edge = math.sqrt(d2) > 1 - 9 / r
        color = fg(level)
        if edge:
            char = stroke(v, u, "_")
            color = fg(level + 0.2)
        elif on_band:
            char = "+" if on_rib else "-"
            color = fg(level + 0.12)
        elif on_rib:
            char = stroke(-math.sin(lat) * math.sin(lon), -math.cos(lat))
            color = fg(level + 0.08)
        elif windows and abs(y - window_y) < CH / 2 and \
                r * math.cos(lat) * abs(math.sin(lon) - math.sin((k + math.copysign(0.5, lon - k * rib)) * rib)) < CW / 2:
            char, color = "o", ("Y" if level > 0.5 else "y")
        elif level > 0.96:
            char = "#"
        else:
            char = plates[min(int(level * len(plates)), len(plates) - 1)]
        put(col, row, char, color, hull(level))


def drum():
    """Colonnade cylinder: columns wrap around, windows sit in the shaded recesses."""
    step = math.radians(7.2)
    for col, row, x, y in cells(AXIS - DRUM_R, 69 * CH, AXIS + DRUM_R, 84 * CH):
        u = (x - AXIS) / DRUM_R
        if abs(u) > 1:
            continue
        theta = math.asin(u)
        level = shade(u, 0, math.cos(theta))
        k = round(theta / step)
        xk = AXIS + DRUM_R * math.sin(k * step)
        half = max(5.0, 14 * math.cos(k * step))
        if abs(x - xk) <= half:
            if row == 69:
                char = "H"
            elif row == 83:
                char = "="
            else:
                char = "|"
            put(col, row, char, fg(level + (0.12 if x < xk else -0.08)), hull(level * 0.8))
        elif row == 69 or row == 83:
            put(col, row, "_", fg(level - 0.2), hull(level * 0.35))
        elif row == 71:
            put(col, row, "^", "C", hull(level * 0.3))
        elif 72 <= row <= 81:
            # Tall windows: a mullion down the middle, one transom, a glint on the lit side.
            middle = AXIS + DRUM_R * math.sin((k + (0.5 if x > xk else -0.5)) * step)
            if abs(x - middle) < CW / 2:
                char = "|"
            elif row == 76:
                char = "-"
            elif level > 0.55 and hsh(col, row, 9) % 9 == 0:
                char = "/"
            else:
                char = " "
            put(col, row, char, "C" if char == "/" else "c", GLASS)
        else:
            put(col, row, " ", "K", hull(level * 0.25))


def rotunda():
    lantern()
    dome(AXIS, DOME_Y, DOME_R, 9, (18, 40, 60), windows=True)
    # Attic band the dome sits on: round windows between short pilasters.
    band(62, 584, "(", "=", ")", facade_light)
    band(63, 584, "(", lambda c: "o" if c % 6 == 0 else "|" if c % 6 == 3 else " ", ")", facade_light)
    band(64, 584, "(", "-", ")", facade_light)
    # Cornice: heavy line, dentils, a fillet and the frieze over the columns.
    band(65, 624, "+", "=", "+", lambda u: facade_light(u) + 0.12)
    band(66, 620, "|", lambda c: "'" if c % 2 else ".", "|", facade_light)
    band(67, 616, "|", "-", "|", facade_light)
    band(68, 608, "[", lambda c: "=" if c % 8 else "#", "]", facade_light)
    drum()
    # Lower cornice tapering into the underside, which steps in toward the dock.
    band(84, 612, "\\", "=", "/", facade_light)
    band(85, 596, "\\", "-", "/", lambda u: facade_light(u) - 0.1)
    band(86, 580, "\\", "_", "/", lambda u: facade_light(u) - 0.2)
    for row, offset in ((87, 560), (89, 520), (91, 480)):
        band(row, offset, "+", "=", "+", lambda u: facade_light(u) - 0.15)
        band(row + 1, offset, "'", lambda c: "-:"[(c // 3) % 2], "'", lambda u: facade_light(u) - 0.25)
    band(93, 200, ".", "-", ".", lambda u: facade_light(u) - 0.1)


def lantern():
    """Cupola on the crown: base ring, small colonnade, cap dome, statue and the lamp."""
    band(25, 88, ".", "=", ".", facade_light)
    band(26, 96, "'", "=", "'", lambda u: facade_light(u) - 0.1)
    for row in range(19, 25):
        c0, c1 = col_at(64, -1), col_at(64, 1)
        for col in range(c0, c1 + 1):
            u = (col * CW + CW / 2 - AXIS) / 64
            level = shade(u, 0, math.sqrt(max(0.0, 1 - u * u)))
            if (col - c0) % 3 == 0:
                put(col, row, "H" if row == 19 else "|", fg(level + 0.1), hull(level * 0.7))
            else:
                put(col, row, ":" if row > 19 else "_", "c", GLASS)
    dome(AXIS, 304, 72, 30, (30,), crown=60)
    statue = [
        ("   *   ", "G"),
        ("   |\\  ", "y"),
        ("  _o/  ", "Y"),
        ("  /|   ", "y"),
        ("  /|\\  ", "C"),
        (" /_|_\\ ", "C"),
        ("[=====]", "y"),
    ]
    c0 = col_at(0, 1) - 3
    for i, (line, color) in enumerate(statue):
        for j, char in enumerate(line):
            if char != " ":
                put(c0 + j, 7 + i, char, color)
    for dc, dr, char in ((-1, 0, "."), (1, 0, "."), (0, -1, "'"), (-2, -1, "."), (2, -1, ".")):
        put(c0 + 3 + dc, 7 + dr, char, "g")


# ---------------------------------------------------------------- underside

def stack(side, offset, first, last, tank):
    """Service stack hanging off the underside: coupler, pipe with valves, nozzle, vapour."""
    c = col_at(offset, side)
    left = c - 1
    lit, dim = ("C", "c") if side < 0 else ("c", "K")
    for row in range(first, last + 1):
        run = row - first
        if run == 0:
            line = "[=]"
        elif row == last:
            line = "\\:/"
        elif run % 7 == 0:
            line = "(o)"
        elif run % 7 == 4:
            line = "==="
        else:
            line = "|:|"
        for dc, char in enumerate(line):
            put(left + dc, row, char, lit if dc == 0 else "y" if char == "o" else dim, HULL[1])
    if tank:
        top = first + 9
        shape = ["  .---.  ", " /|=:=|\\ ", "( |:::| )", "( |:::| )", " \\|=:=|/ ", "  '---'  "]
        for dr, line in enumerate(shape):
            for dc, char in enumerate(line):
                if char != " ":
                    put(left - 3 + dc, top + dr, char, lit if dc < 4 else dim, HULL[1])
    for dr, char in enumerate(":.:."):
        put(left + 1, last + 1 + dr, char, "K" if dr < 2 else "k")


def dock():
    """South dome over the bay. The mouth is the access point; below it stays open."""
    dome(AXIS, DOCK_Y, DOCK_R, 15, (25, 52), crown=70)
    x0, y0, x1, y1 = BAY
    wall0, wall1 = AXIS - DOCK_R, AXIS + DOCK_R
    for col, row, x, y in cells(wall0, DOCK_Y, wall1, y1 + CH):
        u = (x - AXIS) / DOCK_R
        level = 0.1 + 0.9 * shade(u, 0, math.sqrt(max(0.0, 1 - u * u)))
        inside = x0 <= x < x1 and y0 <= y < y1
        if y >= y1 and x0 - CW * 2 <= x < x1 + CW * 2:
            continue
        if inside:
            continue
        if row == int(y0 // CH) - 1 and x0 - CW * 2 <= x < x1 + CW * 2:
            char, color = "\\", ("W" if col % 2 else "O")
            put(col, row, char, color, HULL[0])
            continue
        char = "|" if col % 4 == 0 else "#" if level > 0.55 and hsh(col, row) % 3 == 0 else ":"
        put(col, row, char, fg(level), hull(level * 0.8))
    # Frame posts: amber brackets with yellow inner rails.
    c0, c1 = int(x0 // CW) - 2, int(x1 // CW) + 1
    for row in range(int(y0 // CH), int(y1 // CH)):
        put(c0, row, "[", "O", HULL[0])
        put(c0 + 1, row, "|", "W", VOID)
        put(c1 - 1, row, "|", "W", VOID)
        put(c1, row, "]", "O", HULL[0])
    # Hangar interior: ceiling lights, a back wall with a lit strip, and a deck whose
    # guide lines converge on the cradle.
    r0 = int(y0 // CH)
    vx, vy = AXIS, y0 + 3 * CH
    for col, row, x, y in cells(x0, y0, x1, y1):
        r = row - r0
        char, color = " ", "k"
        if r == 0:
            char, color = ("'", "W") if col % 6 == 0 else ("_", "k")
        elif r <= 2:
            if col % 8 == 0:
                char, color = "|", "K"
            elif r == 2 and abs(x - AXIS) < 160:
                char, color = "=", "c"
            elif r == 1:
                char = "-"
        elif r == 3:
            char, color = "_", "K"
        else:
            top, bottom = (row * CH - vy) / (y1 - vy), ((row + 1) * CH - vy) / (y1 - vy)
            for edge in (x0 + 24, x1 - 24):
                lo, hi = sorted((vx + (edge - vx) * top, vx + (edge - vx) * bottom))
                if lo - CW / 2 <= x <= hi + CW / 2:
                    char, color = "_", "K"
        put(col, row, char, color, VOID)
    # Amber lamps ride the guide lines; the centre line is dashed down the axis.
    for row in range(r0 + 4, int(y1 // CH)):
        depth = (row * CH + CH / 2 - vy) / (y1 - vy)
        lamp = int((vx + (x0 + 24 - vx) * depth) // CW)
        put(lamp, row, "o", "O", VOID)
        put(COLS - 1 - lamp, row, "o", "O", VOID)
        if row % 2 == 0:
            put(col_at(0, 1), row, ":", "W", VOID)
    for dc, char in enumerate("[=[]=]"):
        put(col_at(24, -1) + dc, r0 + 4, char, "C", VOID)
    for side in (-1, 1):
        lamp = col_at(DOCK_R + 36, side)
        put(lamp, int(y0 // CH) + 2, "*", "G")
        put(lamp, int(y0 // CH) + 1, "'", "g")
        put(lamp, int(y0 // CH) + 3, ".", "g")


def main():
    ring(front=False)
    for side in (-1, 1):
        mast(side)
    for side in (-1, 1):
        wing(side)
    rotunda()
    for side in (-1, 1):
        for i, (offset, first, last) in enumerate(STACKS):
            stack(side, offset, first, last, tank=i == 1)
    ring(front=True)
    dock()

    pixels = canvas.render()
    target = REPO / "space" / "assets" / "img" / "objects" / "space_station2.png"
    target.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(pixels).save(target)
    lines = ["".join(canvas.cells.get((x, y), (" ", None, None))[0] for x in range(COLS)).rstrip()
             for y in range(ROWS)]
    (ROOT / "station.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    # Verify every 8x16 tile matches its literal glyph and declared background.
    for (x, y), (ch, fg_hex, bg_hex) in canvas.cells.items():
        tile = pixels[y * CH:(y + 1) * CH, x * CW:(x + 1) * CW]
        expected = np.zeros((CH, CW, 4), dtype=np.uint8)
        if bg_hex is not None:
            expected[:, :, :3] = art.hex_rgb(bg_hex)
            expected[:, :, 3] = 255
        if ch != " ":
            mask = canvas.glyph(ch)
            expected[mask, :3] = art.hex_rgb(fg_hex)
            expected[mask, 3] = 255
        assert np.array_equal(tile, expected), (x, y, ch)
    x0, y0, x1, y1 = BAY
    assert pixels.shape == (SIZE, SIZE, 4)
    assert set(np.unique(pixels[:, :, 3])) == {0, 255}
    assert not np.any(pixels[y1 + CH:, x0:x1, 3]), "South approach must stay open"
    bay = [int((x0 + x1) / 2), int((y0 + y1) / 2)]
    report = {"size": [SIZE, SIZE], "mode": "RGBA", "cell_size": [CW, CH], "grid": [COLS, ROWS],
              "font": "TeleSys.ttf at 16px", "literal_ascii_only": True,
              "cell_count": len(canvas.cells), "every_cell_matches_font_mask": True,
              "alpha_values": [0, 255], "south_approach_clear": True, "bay_center": bay}
    (ROOT / "validation.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report))


if __name__ == "__main__":
    main()
