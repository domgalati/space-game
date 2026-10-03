"""Generate the three space-mode art direction samples.

Sample PNGs are written under space/assets/img/_style_samples/. This file stays
in tools/art/ so it is not part of the game tree. The shipping Nexum Astra
station is written by capitol/generate_station.py, not by this script.

    barge6frame.png             288x48, six 48x48 north-facing frames
    planets/Lava.png            576x576 Terramonta disk, lit from the upper left
    objects/space_station2.png  384x384 Nexum Astra, docking bay on the east face

Alpha is strictly 0 or 255 so rotation and blitting stay crisp.
Terramonta's surface uses the same noise seed as scan_art.py, so the flight
disk and the scan-terminal ASCII show the same fissure network.

The live flight art is larger than the samples, on the same 8x16 cells:

    planets/{Lava,Terran,Ice,Baren}.png  2304x2304 disks, radius 1072
    planets/Sun.png                      3712x3712 sun, radius 1700

Run: python tools/art/qud_glyph/generate_samples.py
     python tools/art/qud_glyph/generate_samples.py flight   (live planets + sun)
"""

from __future__ import annotations

import math
import random
import sys
import zlib
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

# This script lives outside the game tree. Samples are written into assets; the
# script itself is not.
REPO = Path(__file__).resolve().parents[3]
SAMPLES = REPO / "space" / "assets" / "img" / "_style_samples"
FONT_PATH = REPO / "space" / "assets" / "fonts" / "TeleSys.ttf"

FRAME = 48
FRAMES = 6
PLANET = 576
STATION = 384
# Live disks are four times the samples with the same 268/576 margin for the limb
# dots. planet.py derives the disk radius and starport from the image width.
FLIGHT_PLANET = 2304
FLIGHT_RADIUS = FLIGHT_PLANET * 268 // 576

_L = np.array([-0.55, -0.45, 0.70])
LIGHT = _L / np.linalg.norm(_L)

BAYER4 = (np.array([[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]]) + 0.5) / 16.0
CHECKER = np.array([[0.25, 0.75], [0.75, 0.25]])


def hex_rgb(value):
    value = value.lstrip("#")
    return tuple(int(value[i:i + 2], 16) for i in (0, 2, 4))


# ---------------------------------------------------------------- noise

def scan_noise(name):
    """Vectorised copy of scan_art._make_noise seeded the same way."""
    rng = random.Random(zlib.crc32(name.encode("utf-8")))
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
        value = sum(a * np.sin(kx * x + ky * y + kz * z + phase) for kx, ky, kz, phase, a in terms)
        return 1.6 * value / total

    return noise


def _hash(ix, iy, iz, seed):
    h = (ix * 73856093) ^ (iy * 19349663) ^ (iz * 83492791) ^ seed
    h &= 0xFFFFFFFF
    h = ((h ^ (h >> 13)) * 1274126177) & 0xFFFFFFFF
    h ^= h >> 16
    return (h & 0xFFFFFF) / float(0xFFFFFF) * 2.0 - 1.0


def value_noise(x, y, z, seed):
    x0, y0, z0 = np.floor(x), np.floor(y), np.floor(z)
    fx, fy, fz = x - x0, y - y0, z - z0
    fx, fy, fz = (f * f * (3 - 2 * f) for f in (fx, fy, fz))
    ix, iy, iz = (v.astype(np.int64) for v in (x0, y0, z0))
    out = 0.0
    for dx in (0, 1):
        wx = fx if dx else 1 - fx
        for dy in (0, 1):
            wy = fy if dy else 1 - fy
            for dz in (0, 1):
                wz = fz if dz else 1 - fz
                out = out + wx * wy * wz * _hash(ix + dx, iy + dy, iz + dz, seed)
    return out


def fbm(x, y, z, seed, octaves, lacunarity=2.0, gain=0.5):
    total, amp, norm = 0.0, 1.0, 0.0
    for i in range(octaves):
        total = total + amp * value_noise(x, y, z, seed + i * 101)
        norm += amp
        amp *= gain
        x, y, z = x * lacunarity, y * lacunarity, z * lacunarity
    return total / norm


# ---------------------------------------------------------------- quantising

def banded(level, steps, matrix, spread):
    """Map 0..1 onto band indices; ordered dither only near band seams."""
    h, w = level.shape
    tiled = np.tile(matrix, (h // matrix.shape[0] + 1, w // matrix.shape[1] + 1))[:h, :w]
    v = np.clip(level, 0, 0.9999) * (steps - 1)
    base = np.floor(v)
    threshold = 0.5 + (tiled - 0.5) * spread
    return np.clip(base + (v - base > threshold), 0, steps - 1).astype(int)


def upscale(rgba, factor):
    return np.repeat(np.repeat(rgba, factor, axis=0), factor, axis=1)


def save(rgba, *parts):
    path = SAMPLES.joinpath(*parts)
    path.parent.mkdir(parents=True, exist_ok=True)
    rgba = rgba.copy()
    rgba[..., 3] = np.where(rgba[..., 3] > 0, 255, 0)
    rgba[rgba[..., 3] == 0, :3] = 0
    Image.fromarray(rgba.astype(np.uint8), "RGBA").save(path)
    print("wrote", path.relative_to(SAMPLES), rgba.shape[1], "x", rgba.shape[0])


def paint(shape, mask_colors):
    """Compose an RGBA array from (mask, rgb) pairs, later pairs on top."""
    out = np.zeros(shape + (4,), dtype=np.uint8)
    for mask, color in mask_colors:
        out[mask, :3] = color
        out[mask, 3] = 255
    return out


def ramp_lookup(ramp, idx):
    table = np.array([hex_rgb(c) for c in ramp], dtype=np.uint8)
    return table[np.clip(idx, 0, len(ramp) - 1)]


# ---------------------------------------------------------------- planet fields

def terramonta_fields(n, radius, name="Terramonta"):
    """Surface fields for an n x n image whose disk has `radius` pixels."""
    c = n / 2.0
    yy, xx = np.mgrid[0:n, 0:n] + 0.5
    nx, ny = (xx - c) / radius, (yy - c) / radius
    d2 = nx * nx + ny * ny
    inside = d2 <= 1.0
    nz = np.sqrt(np.clip(1.0 - d2, 0.0, 1.0))

    base = scan_noise(name)(nx, ny, nz)
    tex = base - np.median(base[inside])
    warp = fbm(nx * 4 + 3, ny * 4, nz * 4, 11, 4)
    rift = np.abs(tex + 0.10 * warp)
    cracks = np.abs(fbm(nx * 2.4 - 5, ny * 2.4 + 1, nz * 2.4, 41, 5))
    fissure = np.minimum(rift, cracks * 2.0 + 0.03)

    relief = fbm(nx * 3 + 7, ny * 3 - 2, nz * 3, 23, 5)

    rng = random.Random(zlib.crc32(f"{name}-craters".encode("utf-8")))
    height = 0.35 * relief
    for _ in range(26):
        v = np.array([rng.gauss(0, 1) for _ in range(3)])
        v /= np.linalg.norm(v)
        if v[2] < -0.2:
            v[2] = -v[2]
        size = rng.uniform(0.05, 0.16)
        dot = np.clip(nx * v[0] + ny * v[1] + nz * v[2], -1, 1)
        d = np.arccos(dot) / size
        bowl = np.where(d < 1.0, (d * d - 1.0) * 0.55, 0.0)
        rim = 0.30 * np.exp(-((d - 1.0) / 0.22) ** 2)
        height = height + (bowl + rim) * size * 5

    gy, gx = np.gradient(height)
    k = radius * 0.012
    mx, my, mz = nx - gx * k, ny - gy * k, nz
    norm = np.sqrt(mx * mx + my * my + mz * mz) + 1e-9
    light = (mx * LIGHT[0] + my * LIGHT[1] + mz * LIGHT[2]) / norm
    limb = (nx * LIGHT[0] + ny * LIGHT[1]) / (np.sqrt(d2) + 1e-9)

    # Dayside rim port — same longitude in every style so the dock reads as a real site.
    dock_dir = np.array([-0.62, -0.48, 0.62])
    dock_dir = dock_dir / np.linalg.norm(dock_dir)
    dock = inside & (nx * dock_dir[0] + ny * dock_dir[1] + nz * dock_dir[2] > 0.975) & (d2 > 0.78)
    return dict(inside=inside, d2=d2, light=light, fissure=fissure, relief=relief,
                height=height, limb=limb, nx=nx, ny=ny, dock=dock)


# ================================================================ STATION GEOMETRY
#
# Shared layout in a 128x128 logical space so all three directions describe
# the same station: solar wings west, radiators south, comms dish north,
# habitat ring + hub, and the docking module with an open bay facing east.

BAY_MOUTH = (116, 57, 124, 71)  # logical x0, y0, x1, y1


def station_parts(size):
    u = size / 128.0
    yy, xx = np.mgrid[0:size, 0:size] + 0.5
    X, Y = xx / u, yy / u
    cx = cy = 64.0
    r = np.hypot(X - cx, Y - cy)
    theta = np.arctan2(Y - cy, X - cx)

    def rect(x0, y0, x1, y1):
        return (X >= x0) & (X < x1) & (Y >= y0) & (Y < y1)

    parts = []

    def add(name, mask, kind, material, **params):
        parts.append(dict(name=name, mask=mask, kind=kind, material=material, **params))

    add("strut", rect(14, 32, 17, 96), "cyl_v", "hull", c=15.5, h=1.5)
    for y0, y1 in ((32, 58), (70, 96)):
        for x0, x1 in ((3, 14), (17, 28)):
            add("solar", rect(x0, y0, x1, y1), "panel", "solar", box=(x0, y0, x1, y1))
    for x0, x1 in ((44, 59), (69, 84)):
        add("radiator", rect(x0, 100, x1, 123), "panel", "radiator", box=(x0, 100, x1, 123))
    add("mast", rect(61, 8, 67, 124), "cyl_v", "hull", c=64, h=3)
    add("spine", rect(3, 61, 104, 67), "cyl_h", "hull", c=64, h=3)
    dish_r = np.hypot(X - 64, Y - 10)
    add("dish", dish_r < 8.5, "sphere", "hull", c=(64, 10), rad=8.5, concave=True)
    add("dishrim", (dish_r >= 6.8) & (dish_r < 8.5), "torus", "hull", c=(64, 10), rmid=7.65, half=0.85)
    for angle in (45, 135, 225, 315):
        a = math.radians(angle)
        along = (X - cx) * math.cos(a) + (Y - cy) * math.sin(a)
        across = -(X - cx) * math.sin(a) + (Y - cy) * math.cos(a)
        add("spoke", (np.abs(across) < 1.2) & (along > 10) & (along < 28), "flat", "hull")
    add("ring", (r > 26) & (r < 37), "torus", "hull", rmid=31.5, half=5.5)
    add("hub", r < 13.5, "sphere", "glass", c=(64, 64), rad=13.5)
    add("dockmod", rect(100, 50, 124, 78), "box", "hull", box=(100, 50, 124, 78))
    add("bay", rect(*BAY_MOUTH), "void", "void")
    return dict(parts=parts, X=X, Y=Y, r=r, theta=theta, u=u)


def station_levels(geo, bevel):
    """Per-pixel label and 0..1 light level for every part."""
    X, Y = geo["X"], geo["Y"]
    shape = X.shape
    label = np.full(shape, -1, dtype=int)
    level = np.zeros(shape)
    for i, part in enumerate(geo["parts"]):
        label[part["mask"]] = i

    def edge_shade(mask, width):
        m = mask
        lit = np.zeros(shape, bool)
        dark = np.zeros(shape, bool)
        for s in range(1, width + 1):
            up = np.zeros(shape, bool); up[s:, :] = m[:-s, :]
            left = np.zeros(shape, bool); left[:, s:] = m[:, :-s]
            down = np.zeros(shape, bool); down[:-s, :] = m[s:, :]
            right = np.zeros(shape, bool); right[:, :-s] = m[:, s:]
            lit |= m & (~up | ~left)
            dark |= m & (~down | ~right)
        return lit, dark

    for i, part in enumerate(geo["parts"]):
        own = label == i
        kind = part["kind"]
        if kind == "cyl_h":
            t = np.clip((Y - part["c"]) / part["h"], -1, 1)
            lv = t * LIGHT[1] + np.sqrt(1 - t * t) * LIGHT[2]
        elif kind == "cyl_v":
            t = np.clip((X - part["c"]) / part["h"], -1, 1)
            lv = t * LIGHT[0] + np.sqrt(1 - t * t) * LIGHT[2]
        elif kind == "sphere":
            px, py = part["c"]
            sx, sy = (X - px) / part["rad"], (Y - py) / part["rad"]
            sz = np.sqrt(np.clip(1 - sx * sx - sy * sy, 0, 1))
            if part.get("concave"):
                sx, sy = -sx, -sy
            lv = sx * LIGHT[0] + sy * LIGHT[1] + sz * LIGHT[2]
            if part.get("concave"):
                lv = 0.15 + 0.6 * lv
        elif kind == "torus":
            tx, ty = part.get("c", (64.0, 64.0))
            tr = np.hypot(X - tx, Y - ty)
            ta = np.arctan2(Y - ty, X - tx)
            t = np.clip((tr - part["rmid"]) / part["half"], -1, 1)
            dx, dy = np.cos(ta), np.sin(ta)
            lv = t * (dx * LIGHT[0] + dy * LIGHT[1]) + np.sqrt(1 - t * t) * LIGHT[2]
        elif kind == "panel":
            x0, y0, x1, y1 = part["box"]
            lv = 0.55 + 0.25 * (((x1 - X) + (y1 - Y)) / ((x1 - x0) + (y1 - y0)) - 0.5)
            lit, dark = edge_shade(own, bevel)
            lv = np.where(lit, 0.85, np.where(dark, 0.2, lv))
        elif kind == "box":
            lv = np.full(shape, 0.55)
            lit, dark = edge_shade(own, bevel * 2)
            lv = np.where(lit, 0.85, np.where(dark, 0.25, lv))
        elif kind == "void":
            lv = np.zeros(shape)
        else:
            lit, dark = edge_shade(own, bevel)
            lv = np.where(lit, 0.75, np.where(dark, 0.3, 0.55))
        level[own] = np.clip(np.asarray(lv)[own] if np.ndim(lv) else lv, 0, 1)
    return label, level


def outline_mask(alpha):
    a = alpha
    grown = a.copy()
    grown[1:, :] |= a[:-1, :]
    grown[:-1, :] |= a[1:, :]
    grown[:, 1:] |= a[:, :-1]
    grown[:, :-1] |= a[:, 1:]
    return grown & ~a


# ================================================================ A: QUD GLYPH
#
# Everything is TeleSys (the ship-computer font) on its native 8x16 cell,
# Caves of Qud palette, solid cell backgrounds, cell-strict silhouettes.

QUD = {
    "k": "#0f3b3a", "K": "#155352", "y": "#b1c9c3", "Y": "#ffffff",
    "r": "#a64a2e", "R": "#d74200", "o": "#f15f22", "O": "#e99f10",
    "w": "#98875f", "W": "#cfc041", "g": "#009403", "G": "#00c420",
    "b": "#0048bd", "B": "#0096ff", "c": "#40a4b9", "C": "#77bfcf",
    "m": "#b154cf", "M": "#da5bd6",
}
QUD_BG = {
    "night": "#06100f", "deep": "#0b1a19", "rust": "#2a120a", "ember": "#4a1a08",
    "hull": "#0b1a19", "panel": "#04142e", "glass": "#0a2a30", "void": "#000000",
}
CELL_W, CELL_H = 8, 16


class GlyphCanvas:
    def __init__(self, cols, rows):
        self.cols, self.rows = cols, rows
        self.font = ImageFont.truetype(str(FONT_PATH), 16)
        self.cache = {}
        self.cells = {}

    def set(self, col, row, char, fg, bg=None):
        if 0 <= col < self.cols and 0 <= row < self.rows:
            self.cells[(col, row)] = (char, fg, bg)

    def glyph(self, char):
        if char not in self.cache:
            img = Image.new("L", (CELL_W, CELL_H), 0)
            draw = ImageDraw.Draw(img)
            draw.fontmode = "1"
            draw.text((0, 0), char, font=self.font, fill=255)
            self.cache[char] = np.array(img) > 127
        return self.cache[char]

    def render(self):
        out = np.zeros((self.rows * CELL_H, self.cols * CELL_W, 4), dtype=np.uint8)
        for (col, row), (char, fg, bg) in self.cells.items():
            y, x = row * CELL_H, col * CELL_W
            block = out[y:y + CELL_H, x:x + CELL_W]
            if bg is not None:
                block[..., :3] = hex_rgb(bg)
                block[..., 3] = 255
            if char != " ":
                mask = self.glyph(char)
                block[mask, :3] = hex_rgb(fg)
                block[mask, 3] = 255
        return out


def _cell_hash(col, row, salt=0):
    h = (col * 73856093) ^ (row * 19349663) ^ (salt * 83492791)
    h = ((h ^ (h >> 13)) * 1274126177) & 0xFFFFFFFF
    return (h ^ (h >> 16)) & 0xFFFF


def glyph_planet():
    cols, rows = PLANET // CELL_W, PLANET // CELL_H
    radius = 268.0
    f = terramonta_fields(PLANET, radius)
    canvas = GlyphCanvas(cols, rows)
    bg_ramp = ["#060d0d", "#120b0a", "#22100a", "#36160b", "#4c1e0c"]
    fg_ramp = [QUD["k"], QUD["K"], QUD["r"], QUD["w"], QUD["W"]]
    flats = ".,'`."
    rough = ";:\"'"
    for row in range(rows):
        for col in range(cols):
            py, px = row * CELL_H + CELL_H // 2, col * CELL_W + CELL_W // 2
            d2 = f["d2"][py, px]
            fissure = f["fissure"][py, px]
            relief = f["relief"][py, px]
            height = f["height"][py, px]
            h = _cell_hash(col, row)
            if d2 > 1.0:
                if d2 < 1.13 and f["limb"][py, px] > 0.15 and h % 3:
                    canvas.set(col, row, ":" if h % 2 else ".", QUD["r"])
                continue
            lit = max(f["light"][py, px], 0.0)
            level = min(max(lit * 1.05 + 0.25 * relief, 0.0), 0.999)
            tone = int(level * 5)
            bg, fg = bg_ramp[tone], fg_ramp[tone]
            if fissure < 0.034:
                canvas.set(col, row, "*", QUD["Y"] if h % 4 == 0 else QUD["W"], "#6a2206")
            elif fissure < 0.065:
                canvas.set(col, row, "~", QUD["O"] if lit > 0.15 else QUD["o"], "#3e1406")
            elif fissure < 0.095:
                canvas.set(col, row, "~" if h % 3 else "-", QUD["R"] if lit > 0.3 else QUD["r"], bg)
            elif tone == 0:
                canvas.set(col, row, "." if h % 5 == 0 else " ", QUD["k"], bg)
            elif height < -0.10:
                canvas.set(col, row, "o" if h % 7 == 0 else ".", fg_ramp[max(tone - 1, 1)], bg_ramp[max(tone - 1, 0)])
            elif relief > 0.24 and h % 2 == 0:
                canvas.set(col, row, "^", fg_ramp[min(tone + 1, 4)], bg)
            elif tone >= 3:
                canvas.set(col, row, "▒" if relief > 0.1 else "░", fg, bg)
            elif tone == 2:
                canvas.set(col, row, "░" if h % 3 else rough[h % len(rough)], fg, bg)
            else:
                canvas.set(col, row, flats[h % len(flats)], fg, bg)
            if f["dock"][py, px]:
                canvas.set(col, row, "#", QUD["Y"], "#0a3a18")
    save(canvas.render(), "a_qud_glyph", "planets", "Lava.png")


# Live flight disks. Lava keeps the Terramonta scan seed; the others are the same
# glyph treatment in their own palette. Station art is the capitol generator.
FLIGHT_PLANETS = {
    "Lava.png": ("Terramonta",
                 ["#060d0d", "#120b0a", "#22100a", "#36160b", "#4c1e0c"],
                 ["k", "K", "r", "w", "W"], "r", "#6a2206", "#3e1406"),
    "Terran.png": ("Ageria",
                   ["#06140c", "#0c2414", "#14381c", "#1c4c24", "#286832"],
                   ["k", "g", "G", "y", "Y"], "g", "#1a4a18", "#0e3014"),
    "Ice.png": ("Ferrica",
                ["#061018", "#0c2430", "#123848", "#184c60", "#246070"],
                ["k", "b", "c", "C", "Y"], "c", "#143848", "#0c2838"),
    "Baren.png": ("Etheora",
                  ["#100e0c", "#241c14", "#3a2c1c", "#50402c", "#68543c"],
                  ["k", "w", "W", "y", "Y"], "w", "#3a3018", "#241c10"),
}


def write_flight_planets():
    """Write the style-A disks the game loads under space/assets/img/planets/."""
    out_dir = REPO / "space" / "assets" / "img" / "planets"
    out_dir.mkdir(parents=True, exist_ok=True)
    cols, rows = FLIGHT_PLANET // CELL_W, FLIGHT_PLANET // CELL_H
    radius = float(FLIGHT_RADIUS)
    for filename, (name, bg_ramp, fg_keys, limb, hot_bg, warm_bg) in FLIGHT_PLANETS.items():
        f = terramonta_fields(FLIGHT_PLANET, radius, name)
        canvas = GlyphCanvas(cols, rows)
        fg_ramp = [QUD[key] for key in fg_keys]
        flats = ".,'`."
        rough = ";:\"'"
        for row in range(rows):
            for col in range(cols):
                py, px = row * CELL_H + CELL_H // 2, col * CELL_W + CELL_W // 2
                d2 = f["d2"][py, px]
                fissure = f["fissure"][py, px]
                relief = f["relief"][py, px]
                height = f["height"][py, px]
                h = _cell_hash(col, row)
                if d2 > 1.0:
                    if d2 < 1.13 and f["limb"][py, px] > 0.15 and h % 3:
                        canvas.set(col, row, ":" if h % 2 else ".", QUD[limb])
                    continue
                lit = max(f["light"][py, px], 0.0)
                level = min(max(lit * 1.05 + 0.25 * relief, 0.0), 0.999)
                tone = int(level * 5)
                bg, fg = bg_ramp[tone], fg_ramp[tone]
                if fissure < 0.034:
                    canvas.set(col, row, "*", QUD["Y"] if h % 4 == 0 else QUD["W"], hot_bg)
                elif fissure < 0.065:
                    canvas.set(col, row, "~", QUD["O"] if lit > 0.15 else QUD["o"], warm_bg)
                elif fissure < 0.095:
                    canvas.set(col, row, "~" if h % 3 else "-", fg_ramp[min(tone + 1, 4)], bg)
                elif tone == 0:
                    canvas.set(col, row, "." if h % 5 == 0 else " ", QUD["k"], bg)
                elif height < -0.10:
                    canvas.set(col, row, "o" if h % 7 == 0 else ".", fg_ramp[max(tone - 1, 1)], bg_ramp[max(tone - 1, 0)])
                elif relief > 0.24 and h % 2 == 0:
                    canvas.set(col, row, "^", fg_ramp[min(tone + 1, 4)], bg)
                elif tone >= 3:
                    canvas.set(col, row, "▒" if relief > 0.1 else "░", fg, bg)
                elif tone == 2:
                    canvas.set(col, row, "░" if h % 3 else rough[h % len(rough)], fg, bg)
                else:
                    canvas.set(col, row, flats[h % len(flats)], fg, bg)
                if f["dock"][py, px]:
                    canvas.set(col, row, "#", QUD["Y"], "#0a3a18")
        rgba = canvas.render()
        path = out_dir / filename
        Image.fromarray(rgba.astype(np.uint8), "RGBA").save(path)
        print("wrote", path)


# The star at the middle of the flight map. star_systems.SUN_RADIUS matches SUN_RADIUS.
SUN = 3712
SUN_RADIUS = 1700
# Limb to core. The disk is darkest at the edge so it reads as a sphere at any crop.
SUN_BG = ["#1c0703", "#3a1005", "#5e1a06", "#882a08", "#b0420a", "#d0620e", "#e88a16"]
SUN_FG = ["r", "R", "o", "O", "O", "W", "Y"]
SUN_GRANULES = 5200  # cells of convection over the visible hemisphere, about 8x4 glyphs each
# Spots as (unit vector toward the spot, angular size). Kept off the limb so they read round.
SUN_SPOTS = [((-0.30, -0.18, 0.94), 0.070), ((-0.22, -0.30, 0.93), 0.035),
             ((0.38, 0.22, 0.90), 0.055), ((0.10, 0.46, 0.88), 0.030)]
# Prominence loops as (start angle, end angle, height above the limb in px). Angles in degrees.
SUN_PROMINENCES = [(196, 207, 130), (318, 323, 95), (62, 74, 140), (128, 131, 80), (250, 258, 110)]


def _arc_char(dx, dy):
    """Glyph that follows a pixel-space direction on 8x16 cells."""
    angle = math.degrees(math.atan2(-dy, dx)) % 180
    if angle < 22 or angle >= 158:
        return "~"
    if angle < 68:
        return "/"
    if angle < 112:
        return "|"
    return "\\"


def _granules(nx, ny, nz, count, seed):
    """Cellular convection on the sphere: 0 on the dark lanes, 1 at a granule's middle."""
    rng = np.random.default_rng(seed)
    sites = rng.normal(size=(count, 3))
    sites /= np.linalg.norm(sites, axis=1, keepdims=True)
    sites[:, 2] = np.abs(sites[:, 2])
    amp = rng.uniform(-1, 1, count)
    points = np.stack([nx.ravel(), ny.ravel(), nz.ravel()], axis=1)
    inner = np.zeros(len(points))
    bright = np.zeros(len(points))
    for start in range(0, len(points), 4096):
        dots = points[start:start + 4096] @ sites.T
        top = np.argpartition(-dots, 1, axis=1)[:, :2]
        d = np.arccos(np.clip(np.take_along_axis(dots, top, axis=1), -1, 1))
        order = np.argsort(d, axis=1)
        d = np.take_along_axis(d, order, axis=1)
        nearest = np.take_along_axis(top, order, axis=1)[:, 0]
        inner[start:start + 4096] = d[:, 1] - d[:, 0]
        bright[start:start + 4096] = amp[nearest]
    size = math.sqrt(2.0 / count)
    return (np.clip(inner / size, 0, 1).reshape(nx.shape), bright.reshape(nx.shape))


def write_sun():
    """Limb-darkened glyph star with granulation, spots, prominences and a dotted corona."""
    cols, rows = SUN // CELL_W, SUN // CELL_H
    xs = (np.arange(cols) * CELL_W + CELL_W / 2 - SUN / 2) / SUN_RADIUS
    ys = (np.arange(rows) * CELL_H + CELL_H / 2 - SUN / 2) / SUN_RADIUS
    nx, ny = np.meshgrid(xs, ys)
    r = np.hypot(nx, ny)
    nz = np.sqrt(np.clip(1 - r * r, 0, 1))
    inner, bright = _granules(nx, ny, nz, SUN_GRANULES, 71)
    # Supergranulation: a slow bright network, strongest as faculae toward the limb.
    network = fbm(nx * 6 + 2, ny * 6, nz * 6, 67, 3)
    heat = 0.18 + 0.82 * nz ** 0.5 + 0.10 * (inner - 0.5) + 0.04 * bright + 0.06 * network
    heat = np.clip(heat, 0, 0.999)
    spot = np.zeros_like(r)
    spot_center = np.zeros(r.shape + (2,))
    for (sx, sy, sz), size in SUN_SPOTS:
        n = math.sqrt(sx * sx + sy * sy + sz * sz)
        dot = np.clip((nx * sx + ny * sy + nz * sz) / n, -1, 1)
        value = np.clip(1.6 - np.arccos(dot) / size, 0, 1.6)
        closer = value > spot
        spot = np.where(closer, value, spot)
        spot_center[closer] = (sx / n, sy / n)
    theta = np.arctan2(ny, nx)
    streamer = 0.5 + 0.5 * np.sin(theta * 7 + 2.0 * np.sin(theta * 3))

    canvas = GlyphCanvas(cols, rows)
    fg_ramp = [QUD[key] for key in SUN_FG]
    tones = len(SUN_BG)
    for row in range(rows):
        for col in range(cols):
            rr = r[row, col]
            h = _cell_hash(col, row, 7)
            if rr > 1.0:
                # Corona: dots thin out with height; streamers carry radial streaks.
                density = math.exp(-(rr - 1.0) / 0.03) * (0.25 + 0.75 * streamer[row, col])
                if (h % 1000) / 1000 < density * 0.85:
                    if streamer[row, col] > 0.8 and h % 4 == 0:
                        char = _arc_char(nx[row, col], ny[row, col])
                    else:
                        char = "*" if h % 29 == 0 else ":" if h % 3 == 0 else "'" if h % 3 == 1 else "."
                    color = "O" if rr < 1.015 else "o" if rr < 1.035 else "R" if rr < 1.06 else "r"
                    canvas.set(col, row, char, QUD[color])
                continue
            if rr > 0.994:
                canvas.set(col, row, "^" if h % 3 else "~", QUD["W"] if h % 4 else QUD["O"], SUN_BG[2])
                continue
            s = spot[row, col]
            if s > 1.0:
                canvas.set(col, row, "@" if h % 5 == 0 else "o" if h % 2 else " ", QUD["r"], "#0e0302")
                continue
            if s > 0.0:
                # Penumbra filaments radiate from the umbra.
                cx, cy = spot_center[row, col]
                char = _arc_char(nx[row, col] - cx, ny[row, col] - cy) if h % 3 else ":"
                canvas.set(col, row, char, QUD["o"] if s < 0.5 else QUD["R"], "#2a0a04")
                continue
            tone = int(heat[row, col] * tones)
            bg, fg = SUN_BG[tone], fg_ramp[tone]
            e = inner[row, col]
            if e < 0.16:
                # Intergranular lanes: a cooler tone and sparse dust.
                bg = SUN_BG[max(tone - 1, 0)]
                char = "." if h % 3 == 0 else " "
                fg = fg_ramp[max(tone - 2, 0)]
            elif e < 0.42:
                char = ":" if h % 3 == 0 else "+" if h % 3 == 1 else "="
            elif e < 0.78:
                char = "o" if h % 3 else "*"
            else:
                char = "@" if bright[row, col] > 0.4 else "O"
                fg = fg_ramp[min(tone + 1, tones - 1)]
            canvas.set(col, row, char, fg, bg)

    # Prominences: braided loops standing on the limb, drawn over the corona.
    for start, end, height in SUN_PROMINENCES:
        a0, a1 = math.radians(start), math.radians(end)
        for strand, (offset, twist, color) in enumerate(((0, 0.0, "O"), (14, 0.6, "o"), (-12, -0.5, "R"))):
            last = None
            for i in range(601):
                t = i / 600
                arch = math.sin(math.pi * t)
                a = a0 + (a1 - a0) * t + math.radians(twist) * arch * math.sin(6 * math.pi * t + strand)
                radius = SUN_RADIUS + 6 + (height + offset) * arch
                px = SUN / 2 + radius * math.cos(a)
                py = SUN / 2 + radius * math.sin(a)
                col, row = int(px // CELL_W), int(py // CELL_H)
                if last is not None and (col, row) != last[:2]:
                    canvas.set(col, row, _arc_char(px - last[2], py - last[3]), QUD[color])
                last = (col, row, px, py)

    rgba = canvas.render()
    path = REPO / "space" / "assets" / "img" / "planets" / "Sun.png"
    Image.fromarray(rgba.astype(np.uint8), "RGBA").save(path)
    print("wrote", path)


def glyph_station():
    """Nexum Astra as the live Capitol-station silhouette, in TeleSys cells."""
    cols, rows = STATION // CELL_W, STATION // CELL_H
    canvas = GlyphCanvas(cols, rows)
    # Pixel center sits high so the hanging stacks have room under the steps.
    cx, cy = STATION / 2.0, 148.0
    rx, ry = 168.0, 70.0
    dome_r = 58.0
    drum_r = 74.0

    def cell_xy(col, row):
        return (col + 0.5) * CELL_W, (row + 0.5) * CELL_H

    def dome_lit(col, row):
        x, y = cell_xy(col, row)
        nx, ny = (x - cx) / dome_r, (y - cy) / dome_r
        d2 = nx * nx + ny * ny
        nz = math.sqrt(max(0.0, 1.0 - d2))
        return max(0.0, nx * LIGHT[0] + ny * LIGHT[1] + nz * LIGHT[2])

    shade = (
        (0.22, ".", QUD["k"], QUD_BG["deep"]),
        (0.40, "░", QUD["K"], QUD_BG["hull"]),
        (0.58, "▒", QUD["c"], QUD_BG["hull"]),
        (0.74, "▓", QUD["y"], QUD_BG["hull"]),
        (0.88, "▓", QUD["W"], QUD_BG["hull"]),
        (1.01, "█", QUD["Y"], "#2a4030"),
    )

    # Closed oval ring: solve the ellipse per column so the 8x16 grid does not drop arcs.
    for col in range(cols):
        x = (col + 0.5) * CELL_W
        t = 1.0 - ((x - cx) / rx) ** 2
        if t < 0:
            continue
        dy = ry * math.sqrt(max(t, 0.0))
        for sign in (-1.0, 1.0):
            y = cy + sign * dy
            row = int(y // CELL_H)
            ang = math.atan2(y - cy, x - cx)
            flat = abs(math.cos(ang)) > 0.55
            rib = abs(math.sin(ang * 6)) < 0.22
            ch = "+" if rib else ("-" if flat else "|")
            fg = QUD["y"] if rib else QUD["C"]
            canvas.set(col, row, ch, fg, QUD_BG["deep"])
            # One-cell halo so the ring reads as a band, not a wire.
            for dr, fringe in ((-1, "."), (1, ":")):
                if not rib:
                    canvas.set(col, row + dr, fringe, QUD["K"], None)

    # House / Senate wings — hab blocks punched through the ring.
    for west in (True, False):
        c0, c1 = (6, 17) if west else (31, 42)
        for row in range(10, 14):
            for col in range(c0, c1):
                edge = row in (10, 13) or col in (c0, c1 - 1)
                if edge:
                    if row == 10 and col == c0:
                        ch = "┌"
                    elif row == 10 and col == c1 - 1:
                        ch = "┐"
                    elif row == 13 and col == c0:
                        ch = "└"
                    elif row == 13 and col == c1 - 1:
                        ch = "┘"
                    elif row in (10, 13):
                        ch = "─"
                    else:
                        ch = "│"
                    canvas.set(col, row, ch, QUD["y"], QUD_BG["hull"])
                else:
                    office = (col + row) % 2 == 0
                    canvas.set(col, row, "#" if office else "░",
                               QUD["C"] if office else QUD["K"], QUD_BG["panel"])
        # Wing-root airlock toward the dome.
        join_col = c1 if west else c0 - 1
        canvas.set(join_col, 11, "═", QUD["y"], QUD_BG["hull"])
        canvas.set(join_col, 12, "═", QUD["y"], QUD_BG["hull"])

    # Dome drum (wider colonnade) then the rotunda itself.
    for row in range(rows):
        for col in range(cols):
            x, y = cell_xy(col, row)
            d = math.hypot(x - cx, y - cy)
            if 64.0 <= d < drum_r and 7 <= row <= 13:
                ang = math.atan2(y - cy, x - cx)
                col_slot = abs(math.sin(ang * 8)) < 0.22
                canvas.set(col, row, "║" if col_slot else "░",
                           QUD["w"] if col_slot else QUD["K"], QUD_BG["hull"])
            if d < dome_r and 6 <= row <= 12:
                lv = dome_lit(col, row)
                for cut, ch, fg, bg in shade:
                    if lv < cut:
                        canvas.set(col, row, ch, fg, bg)
                        break

    # Lantern / statue — the north beacon. ASCII only; TeleSys lacks the triangles.
    canvas.set(24, 3, "*", QUD["G"], None)
    canvas.set(24, 4, "|", QUD["y"], None)
    canvas.set(24, 5, "^", QUD["W"], QUD_BG["hull"])
    canvas.set(23, 6, "#", QUD["y"], QUD_BG["hull"])
    canvas.set(24, 6, "#", QUD["Y"], QUD_BG["hull"])
    canvas.set(25, 6, "#", QUD["y"], QUD_BG["hull"])

    # South steps = the access corridor. Chevrons point at the bay mouth.
    for col in range(21, 28):
        canvas.set(col, 13, "=" if col not in (21, 27) else "+", QUD["C"], QUD_BG["hull"])
    canvas.set(21, 14, "|", QUD["C"], QUD_BG["hull"])
    canvas.set(27, 14, "|", QUD["C"], QUD_BG["hull"])
    for col, ch in ((22, "<"), (23, "<"), (24, "+"), (25, ">"), (26, ">")):
        canvas.set(col, 14, ch, QUD["W"] if ch == "+" else QUD["O"], QUD_BG["void"])
    canvas.set(21, 15, "+", QUD["C"], QUD_BG["hull"])
    canvas.set(27, 15, "+", QUD["C"], QUD_BG["hull"])
    for col in range(22, 27):
        canvas.set(col, 15, "v", QUD["O"] if col == 24 else QUD["w"], QUD_BG["hull"])
    canvas.set(20, 14, "*", QUD["G"], None)
    canvas.set(28, 14, "*", QUD["G"], None)

    # Hanging stacks / fuel lines under the rotunda — the dripping Capitol underside.
    drip_cols = (16, 19, 22, 24, 26, 29, 32)
    for col in drip_cols:
        length = 3 + _cell_hash(col, 16, 9) % 4
        for i in range(length):
            row = 16 + i
            if row >= rows:
                break
            ch = "|" if i == 0 else (";" if i < length - 1 else (":" if _cell_hash(col, row) % 2 else "."))
            canvas.set(col, row, ch, QUD["K"] if i > 1 else QUD["c"], None)

    save(canvas.render(), "a_qud_glyph", "objects", "space_station2.png")


# Handmade 8x8 CP437 stamps — TeleSys is 8x16 and turns to stripes when squashed.
_GLYPH8 = {
    "X": [  # full block
        "11111111", "11111111", "11111111", "11111111",
        "11111111", "11111111", "11111111", "11111111",
    ],
    "D": [  # dark shade
        "10101010", "01010101", "10101010", "01010101",
        "10101010", "01010101", "10101010", "01010101",
    ],
    "L": [  # light shade
        "10001000", "00000000", "00100010", "00000000",
        "10001000", "00000000", "00100010", "00000000",
    ],
    "[": [
        "01111110", "01100000", "01100000", "01100000",
        "01100000", "01100000", "01100000", "01111110",
    ],
    "]": [
        "01111110", "00000110", "00000110", "00000110",
        "00000110", "00000110", "00000110", "01111110",
    ],
    "+": [
        "00011000", "00011000", "00011000", "11111111",
        "11111111", "00011000", "00011000", "00011000",
    ],
    "n": [  # nav lamp
        "00011000", "00111100", "01111110", "01111110",
        "00111100", "00011000", "00000000", "00000000",
    ],
    "^": [
        "00011000", "00111100", "01100110", "11000011",
        "00000000", "00000000", "00000000", "00000000",
    ],
    "v": [
        "00000000", "00000000", "00000000", "00000000",
        "11000011", "01100110", "00111100", "00011000",
    ],
    "!": [
        "00011000", "00011000", "00011000", "00011000",
        "00011000", "00000000", "00011000", "00011000",
    ],
    "'": [
        "00011000", "00011000", "00001000", "00000000",
        "00000000", "00000000", "00000000", "00000000",
    ],
    '"': [
        "01100110", "01100110", "00100010", "00000000",
        "00000000", "00000000", "00000000", "00000000",
    ],
    ".": [
        "00000000", "00000000", "00000000", "00000000",
        "00000000", "00011000", "00011000", "00000000",
    ],
}


def _stamp8(name):
    return np.array([[ch == "1" for ch in row] for row in _GLYPH8[name]])


# 6x6 cells. Corner pods + cargo brackets so it still reads as the live barge.
GLYPH_SHIP = [
    ".+nn+.",
    "+XDDX+",
    "D[LL]D",
    "D[LL]D",
    "+XDDX+",
    ".+vv+.",
]
GLYPH_SHIP_FG = [
    ".yCCy.",
    "yYwwYy",
    "YwWWwY",
    "YwWWwY",
    "yyyyyy",
    ".ywwy.",
]
GLYPH_SHIP_BG = [
    ".hhhh.",
    "hhhhhh",
    "hh  hh",
    "hh  hh",
    "hhhhhh",
    ".h  h.",
]
GLYPH_FLAMES = [".", "'", '"', "!", '"', "'"]


def glyph_ship():
    sheet = np.zeros((FRAME, FRAME * FRAMES, 4), dtype=np.uint8)
    for i, flame in enumerate(GLYPH_FLAMES):
        frame = np.zeros((FRAME, FRAME, 4), dtype=np.uint8)
        layout = [list(row) for row in GLYPH_SHIP]
        colors = [list(row) for row in GLYPH_SHIP_FG]
        bgs = [list(row) for row in GLYPH_SHIP_BG]
        layout[5][1] = layout[5][4] = flame
        colors[5][1] = colors[5][4] = "Y" if i == 3 else "O" if i in (2, 4) else "o"
        bgs[5][1] = bgs[5][4] = " "
        for row in range(6):
            for col in range(6):
                ch = layout[row][col]
                if ch == ".":
                    continue
                y, x = row * 8, col * 8
                block = frame[y:y + 8, x:x + 8]
                bg = bgs[row][col]
                if bg == "h":
                    block[..., :3] = hex_rgb(QUD_BG["hull"])
                    block[..., 3] = 255
                ink = _stamp8(ch)
                block[ink, :3] = hex_rgb(QUD[colors[row][col]])
                block[ink, 3] = 255
        sheet[:, i * FRAME:(i + 1) * FRAME] = frame
    save(sheet, "a_qud_glyph", "barge6frame.png")


# ================================================================ B: NES CARTRIDGE
#
# Real 2C02 palette entries, art authored on a coarse grid and upscaled 3x
# (ship 16x16, station 128x128, planet 192x192 logical), hard bands with
# checkerboard seams, black sprite outlines.

NES = {
    "0F": "#000000", "2D": "#4f4f4f", "00": "#7c7c7c", "10": "#bcbcbc", "20": "#f8f8f8",
    "02": "#0000bc", "12": "#0058f8", "21": "#3cbcfc", "31": "#a4e4fc",
    "06": "#a81000", "07": "#881400", "08": "#503000", "16": "#f83800", "17": "#e45c10",
    "27": "#fca044", "28": "#f8b800", "38": "#f8d878", "30": "#fcfcfc", "2C": "#00e8d8",
    "1A": "#00a800", "18": "#ac7c00",
}
NES_SCALE = 3


def nes_planet():
    n = PLANET // NES_SCALE
    radius = 90.0
    f = terramonta_fields(n, radius)
    inside = f["inside"]
    lit = np.clip(f["light"], 0, 1)
    crust_ramp = [NES[k] for k in ("08", "07", "06", "17", "27")]
    level = 0.05 + 0.9 * lit + 0.3 * f["relief"]
    idx = banded(level, len(crust_ramp), CHECKER, 0.35)
    rgb = ramp_lookup(crust_ramp, idx)

    lava_ramp = [NES[k] for k in ("06", "16", "28", "38")]
    heat = np.clip(1 - f["fissure"] / 0.07, 0, 1)
    lava_idx = banded(heat, len(lava_ramp), CHECKER, 0.5)
    lava = heat > 0.05
    rgb[lava] = ramp_lookup(lava_ramp, lava_idx)[lava]

    haze = (~inside) & (f["d2"] < 1.07) & (f["limb"] > 0.25)
    haze &= (np.indices(f["d2"].shape).sum(axis=0) % 2 == 0)
    out = np.zeros((n, n, 4), dtype=np.uint8)
    out[inside, :3] = rgb[inside]
    out[inside, 3] = 255
    out[haze, :3] = hex_rgb(NES["07"])
    out[haze, 3] = 255
    dock = f["dock"]
    out[dock, :3] = hex_rgb(NES["2C"])
    ring = inside & (~dock) & (f["d2"] > 0.86) & (
        (f["nx"] * -0.62 + f["ny"] * -0.48 + np.sqrt(np.clip(1 - f["d2"], 0, 1)) * 0.62) > 0.955)
    out[ring, :3] = hex_rgb(NES["20"])
    save(upscale(out, NES_SCALE), "b_nes_cartridge", "planets", "Lava.png")


NES_MATERIALS = {
    "hull": ("2D", "00", "10", "20"),
    "glass": ("02", "12", "21", "31"),
    "solar": ("02", "12", "21"),
    "radiator": ("2D", "10", "20"),
    "void": ("0F",),
}


def nes_station():
    n = STATION // NES_SCALE
    geo = station_parts(n)
    label, level = station_levels(geo, 1)
    out = np.zeros((n, n, 4), dtype=np.uint8)
    X, Y = geo["X"], geo["Y"]
    for i, part in enumerate(geo["parts"]):
        own = label == i
        ramp = [NES[k] for k in NES_MATERIALS[part["material"]]]
        idx = banded(level, len(ramp), CHECKER, 0.4)
        out[own, :3] = ramp_lookup(ramp, idx)[own]
        out[own, 3] = 255
        if part["name"] == "solar":
            grid = own & ((np.floor(X) % 4 == 0) | (np.floor(Y) % 4 == 0))
            out[grid, :3] = hex_rgb(NES["02"])
        if part["name"] == "radiator":
            stripe = own & (np.floor(Y) % 3 == 0)
            out[stripe, :3] = hex_rgb(NES["17"])
        if part["name"] == "bay":
            chevron = own & (np.abs(np.abs(Y - 64) - (X - 117) * 1.0) < 0.6) & (X > 117)
            out[chevron, :3] = hex_rgb(NES["28"])

    ring_window = (label == [p["name"] for p in geo["parts"]].index("ring")) & \
        (np.abs(geo["r"] - 31.5) < 0.6) & (np.floor((geo["theta"] + math.pi) * 18 / math.pi) % 2 == 0)
    out[ring_window, :3] = hex_rgb(NES["38"])

    lights = [((115, 55), "2C"), ((115, 72), "2C"), ((124, 55), "1A"), ((124, 72), "1A"),
              ((3, 63), "16"), ((64, 2), "16")]
    for (lx, ly), key in lights:
        out[ly:ly + 2, lx:lx + 2, :3] = hex_rgb(NES[key])
        out[ly:ly + 2, lx:lx + 2, 3] = 255

    edge = outline_mask(out[..., 3] > 0)
    out[edge, :3] = 0
    out[edge, 3] = 255
    save(upscale(out, NES_SCALE), "b_nes_cartridge", "objects", "space_station2.png")


NES_SHIP = [
    ".KKKKKKKKKKKKKK.",
    ".KWWLSLLLLSLWWK.",
    ".KWLDSRRRRSDLWK.",
    ".KLDDSDDDDSDDLK.",
    ".KSSSSKKKKSSSSK.",
    "..KLDKSKKSKDLK..",
    "..KCDKKSSKKDCK..",
    "..KLDKSKKSKDLK..",
    ".KSSSSKKKKSSSSK.",
    ".KLLLSLLLLSLLLK.",
    ".KLDDSRRRRSDDLK.",
    ".KDDrSDDDDSrDDK.",
    ".KKKKKKKKKKKKKK.",
    "..KSK......KSK..",
    "................",
    "................",
]
NES_SHIP_COLORS = {"K": "0F", "S": "2D", "D": "00", "L": "10", "W": "20", "R": "17", "C": "2C", "r": "16"}
NES_FLAMES = [("16", None), ("27", "16"), ("38", "27"), ("30", "28"), ("28", "16"), ("27", None)]


def nes_ship():
    sheet = np.zeros((FRAME, FRAME * FRAMES, 4), dtype=np.uint8)
    for i, flame in enumerate(NES_FLAMES):
        frame = np.zeros((16, 16, 4), dtype=np.uint8)
        for y, line in enumerate(NES_SHIP):
            for x, ch in enumerate(line):
                if ch != ".":
                    frame[y, x, :3] = hex_rgb(NES[NES_SHIP_COLORS[ch]])
                    frame[y, x, 3] = 255
        for depth, key in enumerate(flame):
            if key is None:
                continue
            for x in (3, 12):
                frame[14 + depth, x, :3] = hex_rgb(NES[key])
                frame[14 + depth, x, 3] = 255
        sheet[:, i * FRAME:(i + 1) * FRAME] = upscale(frame, NES_SCALE)
    save(sheet, "b_nes_cartridge", "barge6frame.png")


# ================================================================ C: HI-RES RAMP
#
# Native 1x pixel art with the Endesga-32 palette: hue-shifted ramps (shadows
# go violet, highlights go warm), 4x4 Bayer dithering only on band seams,
# selective outlines (ramp-dark on the lit side, near-black on the shadow side).

E32 = {
    "ink": "#181425", "navy": "#262b44", "slate": "#3a4466", "steel": "#5a6988",
    "fog": "#8b9bb4", "pale": "#c0cbdc", "white": "#ffffff",
    "plum": "#3e2731", "brick": "#733e39", "clay": "#b86f50", "tan": "#e4a672",
    "rust": "#be4a2f", "terra": "#d77643",
    "wine": "#a22633", "red": "#e43b44", "orange": "#f77622", "amber": "#feae34", "yellow": "#fee761",
    "deep": "#124e89", "blue": "#0099db", "cyan": "#2ce8f5", "teal": "#193c3e",
    "green": "#63c74d",
}


def ramp(*names):
    return [E32[n] for n in names]


def hires_planet():
    radius = 276.0
    f = terramonta_fields(PLANET, radius)
    inside = f["inside"]
    lit = np.clip(f["light"], 0, 1)
    crust = ramp("ink", "navy", "plum", "brick", "clay", "tan")
    detail = fbm(f["nx"] * 40, f["ny"] * 40, f["d2"] * 3, 77, 3)
    level = 0.04 + 0.92 * lit + 0.22 * f["relief"] + 0.05 * detail
    rgb = ramp_lookup(crust, banded(level, len(crust), BAYER4, 0.55))

    glow = np.clip(1 - f["fissure"] / 0.16, 0, 1)
    halo = (glow > 0.0) & (glow < 0.45)
    halo_ramp = ramp("plum", "brick", "rust", "terra")
    halo_idx = np.maximum(banded(glow / 0.45 * 0.9, len(halo_ramp), BAYER4, 0.8),
                          banded(level, len(halo_ramp), BAYER4, 0.8) - 1)
    rgb[halo] = ramp_lookup(halo_ramp, halo_idx)[halo]

    heat = np.clip(1 - f["fissure"] / 0.075, 0, 1)
    lava_ramp = ramp("wine", "red", "orange", "amber", "yellow")
    lava = heat > 0.02
    rgb[lava] = ramp_lookup(lava_ramp, banded(heat, len(lava_ramp), BAYER4, 0.6))[lava]

    out = np.zeros((PLANET, PLANET, 4), dtype=np.uint8)
    out[inside, :3] = rgb[inside]
    out[inside, 3] = 255

    rim = inside & (f["d2"] > 0.985) & (f["limb"] > 0.2)
    out[rim, :3] = hex_rgb(E32["tan"])
    yy, xx = np.indices(f["d2"].shape)
    haze_band = (~inside) & (f["d2"] < 1.045) & (f["limb"] > 0.1)
    haze = haze_band & ((f["d2"] < 1.02) | ((xx + yy) % 2 == 0)) & ((f["d2"] < 1.03) | (xx % 2 == 0))
    out[haze, :3] = hex_rgb(E32["rust"])
    out[haze, 3] = 255
    pad = f["dock"]
    out[pad, :3] = hex_rgb(E32["cyan"])
    apron = inside & (~pad) & (f["d2"] > 0.84) & (
        (f["nx"] * -0.62 + f["ny"] * -0.48 + np.sqrt(np.clip(1 - f["d2"], 0, 1)) * 0.62) > 0.96)
    out[apron, :3] = hex_rgb(E32["pale"])
    save(out, "c_hires_ramp", "planets", "Lava.png")


HIRES_MATERIALS = {
    "hull": ramp("navy", "slate", "steel", "fog", "pale", "white"),
    "glass": ramp("ink", "deep", "blue", "cyan", "white"),
    "solar": ramp("ink", "navy", "deep", "blue", "cyan"),
    "radiator": ramp("plum", "brick", "clay", "tan"),
    "void": ramp("ink"),
}


def hires_station():
    geo = station_parts(STATION)
    label, level = station_levels(geo, 2)
    X, Y, u = geo["X"], geo["Y"], geo["u"]
    names = [p["name"] for p in geo["parts"]]
    out = np.zeros((STATION, STATION, 4), dtype=np.uint8)
    seam = (np.floor(X * u) % 24 == 0) | (np.floor(Y * u) % 24 == 0)
    for i, part in enumerate(geo["parts"]):
        own = label == i
        mat = HIRES_MATERIALS[part["material"]]
        lv = level.copy()
        if part["name"] in ("spine", "mast", "dockmod"):
            lv = np.where(seam, lv - 0.18, lv)
        idx = banded(lv, len(mat), BAYER4, 0.6)
        out[own, :3] = ramp_lookup(mat, idx)[own]
        out[own, 3] = 255
        if part["name"] == "solar":
            x0, y0, x1, y1 = part["box"]
            gx = np.floor((X - x0) * u) % 9 == 0
            gy = np.floor((Y - y0) * u) % 9 == 0
            out[own & (gx | gy), :3] = hex_rgb(E32["ink"])
            glint = own & (np.abs((X - x0) - (Y - y0) * 0.45 - 2) < 0.5)
            out[glint & ~(gx | gy), :3] = hex_rgb(E32["cyan"])
        if part["name"] == "radiator":
            stripe = own & (np.floor((Y - 100) * u) % 6 < 2)
            out[stripe, :3] = hex_rgb(E32["plum"])
        if part["name"] == "bay":
            depth = (X - BAY_MOUTH[0]) / (BAY_MOUTH[2] - BAY_MOUTH[0])
            interior = ramp("ink", "navy", "slate")
            out[own, :3] = ramp_lookup(interior, banded(depth, 3, BAYER4, 0.9))[own]
            for k, offset in enumerate((0.0, 3.0, 6.0)):
                chevron = own & (np.abs(np.abs(Y - 64) - (X - 117.5 - offset) * 1.1) < 0.45) & (X > 117.5 + offset)
                out[chevron, :3] = hex_rgb(E32["amber"] if k == 0 else E32["yellow"])

    ring = label == names.index("ring")
    windows = ring & (np.abs(geo["r"] - 33.5) < 0.9) & (np.floor((geo["theta"] + math.pi) * 30 / math.pi) % 2 == 0)
    windows &= np.floor(geo["theta"] * 60 / math.pi) % 3 != 0
    out[windows, :3] = hex_rgb(E32["yellow"])
    hub = label == names.index("hub")
    hub_win = hub & (np.abs(geo["r"] - 9.5) < 0.6) & (np.floor((geo["theta"] + math.pi) * 8 / math.pi) % 2 == 0) & (Y > 64)
    out[hub_win, :3] = hex_rgb(E32["amber"])

    def light(x, y, color, size=2):
        px, py = int(x * u), int(y * u)
        out[py:py + size, px:px + size, :3] = hex_rgb(E32[color])
        out[py:py + size, px:px + size, 3] = 255

    for y in (55.0, 72.0):
        light(115.5, y, "cyan", 4)
        light(124.0, y, "green", 3)
    for k in range(4):
        light(104 + k * 3.0, 51.0, "cyan", 2)
        light(104 + k * 3.0, 76.2, "cyan", 2)
    light(3.0, 63.0, "red", 3)
    light(63.5, 0.8, "red", 3)

    alpha = out[..., 3] > 0
    edge = outline_mask(alpha)
    below = np.zeros_like(alpha); below[:-1] = alpha[1:]
    rightn = np.zeros_like(alpha); rightn[:, :-1] = alpha[:, 1:]
    lit_side = edge & (below | rightn)
    out[edge, :3] = hex_rgb(E32["ink"])
    out[lit_side, :3] = hex_rgb(E32["navy"])
    out[edge, 3] = 255
    save(out, "c_hires_ramp", "objects", "space_station2.png")


def hires_ship_base():
    s = FRAME
    img = np.zeros((s, s, 4), dtype=np.uint8)
    yy, xx = np.mgrid[0:s, 0:s]
    hull = ramp("navy", "slate", "steel", "fog", "pale")

    def box(x0, y0, x1, y1, mat=hull, base=2):
        m = (xx >= x0) & (xx <= x1) & (yy >= y0) & (yy <= y1)
        img[m, :3] = hex_rgb(mat[base])
        img[m, 3] = 255
        img[m & (yy == y0), :3] = hex_rgb(mat[min(base + 2, len(mat) - 1)])
        img[m & (yy == y0 + 1), :3] = hex_rgb(mat[min(base + 1, len(mat) - 1)])
        img[m & ((xx == x0) | (xx == x1)) & (yy > y0), :3] = hex_rgb(mat[base + 1 if base + 1 < len(mat) else base])
        img[m & (yy == y1), :3] = hex_rgb(mat[max(base - 2, 0)])
        img[m & (yy == y1 - 1), :3] = hex_rgb(mat[max(base - 1, 0)])
        return m

    def mirror_box(x0, y0, x1, y1, **kw):
        box(x0, y0, x1, y1, **kw)
        box(s - 1 - x1, y0, s - 1 - x0, y1, **kw)

    # Cargo frame bars.
    mirror_box(9, 9, 14, 32, base=1)
    box(15, 5, 32, 10, base=2)
    box(15, 30, 32, 35, base=1)
    # Cargo bay well with grid.
    bay = (xx >= 15) & (xx <= 32) & (yy >= 11) & (yy <= 29)
    img[bay, :3] = hex_rgb(E32["ink"])
    img[bay, 3] = 255
    grid = bay & (((xx - 15) % 6 == 0) | ((yy - 11) % 6 == 0))
    img[grid, :3] = hex_rgb(E32["navy"])
    img[bay & (yy == 11), :3] = hex_rgb(E32["ink"])
    img[bay & (yy == 12) & ((xx - 15) % 6 != 0), :3] = hex_rgb(E32["navy"])
    crates = [(16, 18), (22, 24), (28, 12)]
    rust = ramp("plum", "brick", "clay", "tan")
    for cx, cy in crates:
        box(cx, cy, cx + 4, cy + 4, mat=rust, base=2)
    # Rust safety stripes on the top bar.
    stripe = (yy >= 7) & (yy <= 8) & (xx >= 17) & (xx <= 30) & ((xx // 2) % 2 == 0)
    img[stripe, :3] = hex_rgb(E32["clay"])
    # Corner pods.
    for y0 in (3, 28):
        mirror_box(4, y0, 15, y0 + 10, base=3)
        mirror_box(7, y0 + 3, 12, y0 + 7, base=1)
    # Nav lights: cyan bow, red stern.
    for x in (5, 42):
        img[6:8, x:x + 1, :3] = hex_rgb(E32["cyan"])
        img[31:33, x:x + 1, :3] = hex_rgb(E32["red"])
    # Nozzles under the stern pods.
    for x0 in (6, 11, 34, 39):
        box(x0, 39, x0 + 2, 41, base=1)
    alpha = img[..., 3] > 0
    edge = outline_mask(alpha)
    img[edge, :3] = hex_rgb(E32["ink"])
    img[edge, 3] = 255
    return img


def hires_ship():
    base = hires_ship_base()
    lengths = [2, 3, 5, 6, 4, 3]
    flame_ramp = ramp("red", "orange", "amber", "yellow", "white")
    sheet = np.zeros((FRAME, FRAME * FRAMES, 4), dtype=np.uint8)
    for i, length in enumerate(lengths):
        frame = base.copy()
        for x0 in (6, 11, 34, 39):
            jitter = (i + x0) % 2
            ln = min(length + jitter, FRAME - 43)
            for d in range(ln):
                y = 43 + d
                t = 1 - d / max(ln, 1)
                core = flame_ramp[min(4, int(t * 4.99))]
                outer = flame_ramp[max(0, int(t * 4.99) - 2)]
                frame[y, x0 + 1, :3] = hex_rgb(core)
                frame[y, x0 + 1, 3] = 255
                if d < ln - 1:
                    for x in (x0, x0 + 2):
                        frame[y, x, :3] = hex_rgb(outer)
                        frame[y, x, 3] = 255
            frame[42, x0:x0 + 3, :3] = hex_rgb(E32["yellow"] if i in (2, 3) else E32["amber"])
            frame[42, x0:x0 + 3, 3] = 255
        sheet[:, i * FRAME:(i + 1) * FRAME] = frame
    save(sheet, "c_hires_ramp", "barge6frame.png")


def main():
    glyph_ship()
    glyph_planet()
    glyph_station()
    nes_ship()
    nes_planet()
    nes_station()
    hires_ship()
    hires_planet()
    hires_station()


if __name__ == "__main__":
    if sys.argv[1:] == ["flight"]:
        write_flight_planets()
        write_sun()
    else:
        main()
