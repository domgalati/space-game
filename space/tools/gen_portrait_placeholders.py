"""Draw the placeholder portrait layers listed in space/assets/img/portraits/manifest.yaml.

    python space/tools/gen_portrait_placeholders.py [--preview contact_sheet.png]

Tinted parts are grayscale (see the manifest header). Shapes are built as pixel masks, then
shaded in three tones with a one-pixel outline, lit from the top left.
"""
import argparse
import os
import random
import sys
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
import pygame  # noqa: E402

SPACE = Path(__file__).resolve().parents[1]
OUT = SPACE / "assets" / "img" / "portraits"
SIZE = 64
N4 = ((1, 0), (-1, 0), (0, 1), (0, -1))

G_OUTLINE, G_SHADOW, G_BASE, G_HIGHLIGHT = 84, 172, 222, 250

# Per-species anchor points. Everything is symmetric about x = 31.5 (x mirrors to 63 - x).
GEOM = {
    "human": {
        "head": (21, 11, 22, 28), "eye": (25, 4, 23, 3), "forehead": 17,
        "mouth": (33, 29, 34), "cheek_y": 29, "ear": (20, 26), "lobe": (19, 30),
    },
    "vessari": {
        "head": (22, 8, 20, 32), "eye": (25, 6, 21, 4), "forehead": 15,
        "mouth": (34, 30, 33), "cheek_y": 29, "ear": (22, 25), "lobe": None,
    },
    "muroth": {
        "head": (18, 14, 28, 26), "eye": (25, 3, 25, 3), "forehead": 21,
        "mouth": (35, 27, 36), "cheek_y": 31, "ear": (16, 23), "lobe": (17, 27),
    },
}


# Masks: sets of (x, y) pixels.

def ellipse(x, y, w, h):
    cx, cy, rx, ry = x + w / 2, y + h / 2, w / 2, h / 2
    return {
        (px, py)
        for px in range(max(0, int(x)), min(SIZE, int(x + w) + 1))
        for py in range(max(0, int(y)), min(SIZE, int(y + h) + 1))
        if ((px + 0.5 - cx) / rx) ** 2 + ((py + 0.5 - cy) / ry) ** 2 <= 1
    }


def rect(x, y, w, h):
    return {(px, py) for px in range(x, x + w) for py in range(y, y + h) if 0 <= px < SIZE and 0 <= py < SIZE}


def _drawn(draw):
    surface = pygame.Surface((SIZE, SIZE), pygame.SRCALPHA)
    draw(surface)
    return {(x, y) for x in range(SIZE) for y in range(SIZE) if surface.get_at((x, y)).a}


def polygon(points):
    return _drawn(lambda s: pygame.draw.polygon(s, (255, 255, 255), points))


def line(start, end, width=1):
    return _drawn(lambda s: pygame.draw.line(s, (255, 255, 255), start, end, width))


def mirror(mask):
    return {(SIZE - 1 - x, y) for x, y in mask}


def both(mask):
    return mask | mirror(mask)


def rows(mask, low, high):
    return {(x, y) for x, y in mask if low <= y <= high}


# Painting.

def gray(value, alpha=255):
    return (value, value, value, alpha)


def gray_tones(alpha=255):
    return {
        "outline": gray(G_OUTLINE, alpha),
        "shadow": gray(G_SHADOW, alpha),
        "base": gray(G_BASE, alpha),
        "highlight": gray(G_HIGHLIGHT, alpha),
    }


def color_tones(rgb):
    def scale(f):
        return tuple(max(0, min(255, int(c * f))) for c in rgb) + (255,)

    return {"outline": scale(0.4), "shadow": scale(0.72), "base": scale(1.0), "highlight": scale(1.22)}


def shade(surface, mask, tones, outline=True):
    if not mask:
        return
    xs = [x for x, _ in mask]
    ys = [y for _, y in mask]
    cx, cy = (min(xs) + max(xs) + 1) / 2, (min(ys) + max(ys) + 1) / 2
    rx, ry = max(1, (max(xs) - min(xs) + 1) / 2), max(1, (max(ys) - min(ys) + 1) / 2)
    for x, y in mask:
        edge = outline and any(
            (x + dx, y + dy) not in mask
            for dx, dy in N4
            if 0 <= x + dx < SIZE and 0 <= y + dy < SIZE
        )
        if edge:
            color = tones["outline"]
        else:
            d = (x + 0.5 - cx) / rx * 0.75 + (y + 0.5 - cy) / ry * 0.55
            color = tones["shadow"] if d > 0.55 else tones["highlight"] if d < -0.6 else tones["base"]
        surface.set_at((x, y), color)


def fill(surface, mask, color):
    for point in mask:
        surface.set_at(point, color)


def interior(mask):
    return {(x, y) for x, y in mask if all((x + dx, y + dy) in mask for dx, dy in N4)}


def shadow_band(surface, mask, low, high):
    """Darken rows ``low``..``high`` of an already shaded mask, keeping its outline."""
    fill(surface, rows(interior(mask), low, high), gray(G_SHADOW))


def canvas():
    return pygame.Surface((SIZE, SIZE), pygame.SRCALPHA)


def save(surface, relative):
    path = OUT / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    pygame.image.save(surface, str(path))


def head_mask(species):
    g = GEOM[species]
    mask = ellipse(*g["head"])
    if species == "muroth":
        mask |= ellipse(19, 24, 26, 17)
    return mask


# Heads (tint: skin).

def draw_heads():
    tones = gray_tones()
    # Human
    s = canvas()
    shade(s, both(ellipse(18, 22, 5, 8)), tones)
    neck = rect(27, 33, 10, 13)
    shade(s, neck, tones)
    shadow_band(s, neck, 33, 40)
    shade(s, head_mask("human"), tones)
    fill(s, {(33, 26), (33, 27), (33, 28), (32, 29)}, gray(G_SHADOW))
    fill(s, {(31, 29), (33, 29)}, gray(130))
    save(s, "head/human.png")

    # Vessari: tall, narrow, no ears, cheek ridges and a brow spot.
    s = canvas()
    neck = rect(28, 34, 8, 12)
    shade(s, neck, tones)
    shadow_band(s, neck, 34, 42)
    shade(s, head_mask("vessari"), tones)
    fill(s, both({(24, 28), (24, 29), (25, 30), (25, 31)}), gray(150))
    fill(s, both({(31, 13), (31, 14)}), gray(G_HIGHLIGHT))
    fill(s, both({(30, 29)}), gray(120))
    save(s, "head/vessari.png")

    # Muroth: broad jaw, pointed ears, heavy brow ridge, wide nose.
    s = canvas()
    shade(s, both(polygon([(20, 21), (13, 17), (20, 29)])), tones)
    neck = rect(24, 33, 16, 13)
    shade(s, neck, tones)
    shadow_band(s, neck, 33, 41)
    head = head_mask("muroth")
    shade(s, head, tones)
    fill(s, {(x, y) for x, y in head if y in (22, 23) and 20 <= x <= 43}, gray(G_SHADOW))
    fill(s, {(x, 24) for x in range(22, 42)}, gray(135))
    fill(s, {(34, 29), (34, 30), (30, 31), (31, 31), (32, 31), (33, 31)}, gray(G_SHADOW))
    fill(s, {(30, 31), (33, 31)}, gray(120))
    save(s, "head/muroth.png")


# Eyes.

def eye_masks(species):
    x, w, y, h = GEOM[species]["eye"]
    return x, w, y, h


def draw_eyes():
    white = (238, 236, 230, 255)
    lash = (46, 34, 30, 255)

    def human(name, lids):
        x, w, y, h = eye_masks("human")
        base, iris, brows = canvas(), canvas(), canvas()
        top = y + lids
        fill(base, both({(px, top) for px in range(x, x + w)}), lash)
        fill(base, both(rect(x, top + 1, w, h - 1 - lids)), white)
        fill(iris, both(rect(x + 1, top + 1, 2, h - 1 - lids)), gray(120))
        fill(iris, both(rect(x + 1, top + 1, 2, 1)), gray(215 if lids else 235))
        brow_y = y - 2 + lids
        fill(brows, both({(px, brow_y) for px in range(x, x + w)} | {(x - 1, brow_y + 1)}), gray(200))
        if lids:
            fill(brows, both({(px, brow_y - 1) for px in range(x + 1, x + w)}), gray(170))
        save(base, f"eyes/{name}.png")
        save(iris, f"eyes/{name}_iris.png")
        save(brows, f"eyes/{name}_brows.png")

    human("round", 0)
    human("narrow", 1)

    # Muroth: small, deep-set, yellowed whites, thick brows.
    x, w, y, h = eye_masks("muroth")
    base, iris, brows = canvas(), canvas(), canvas()
    fill(base, both({(px, y) for px in range(x, x + w)}), lash)
    fill(base, both(rect(x, y + 1, w, 2)), (228, 212, 168, 255))
    fill(iris, both(rect(x + 1, y + 1, 2, 2)), gray(110))
    fill(iris, both(rect(x + 1, y + 1, 2, 1)), gray(230))
    fill(brows, both(rect(x - 1, y - 3, w + 2, 2)), gray(150))
    save(base, "eyes/deepset.png")
    save(iris, "eyes/deepset_iris.png")
    save(brows, "eyes/deepset_brows.png")

    # Vessari: dark almond eyes with a glowing iris.
    x, w, y, h = eye_masks("vessari")
    dark = (26, 26, 44, 255)
    for name, shape, glow_rows in (
        ("almond", {(px, y) for px in range(x + 1, x + w - 1)} | rect(x, y + 1, w, 2) | {(px, y + 3) for px in range(x + 1, x + w - 1)}, (y + 1, y + 2)),
        ("wide", ellipse(x - 0.5, y - 1, w + 1, h + 2), (y, y + 1, y + 2)),
    ):
        base, glow = canvas(), canvas()
        fill(base, both(shape), dark)
        ring = {(px, py) for px in range(x + 1, x + w - 1) for py in glow_rows}
        core = {(px, py) for px in range(x + 2, x + w - 2) for py in glow_rows}
        fill(glow, both(ring), gray(170))
        fill(glow, both(core), gray(255))
        save(base, f"eyes/{name}.png")
        save(glow, f"eyes/{name}_glow.png")


# Mouths (tint: skin) and tusks.

def draw_mouths():
    def mouth(species, name, dark, light, extra_dark=(), extra_light=()):
        s = canvas()
        fill(s, set(light) | set(extra_light), gray(200))
        fill(s, set(dark) | set(extra_dark), gray(115))
        save(s, f"mouth/{name}_{species}.png")

    for species in GEOM:
        y, left, right = GEOM[species]["mouth"]
        full = [(x, y) for x in range(left, right + 1)]
        inner = [(x, y) for x in range(left + 1, right)]
        lip = [(x, y + 1) for x in range(left + 1, right)]
        mouth(species, "neutral", full, lip)
        mouth(species, "smile", inner, lip, extra_dark=[(left, y - 1), (right, y - 1)])
        if species != "vessari":
            mouth(species, "stern", full, [], extra_dark=[(left - 1, y + 1), (right + 1, y + 1)],
                  extra_light=[(31, y + 3), (32, y + 3)])

    ivory, ivory_shadow = (238, 228, 198, 255), (186, 172, 140, 255)
    y, left, right = GEOM["muroth"]["mouth"]
    small, large = canvas(), canvas()
    fill(small, both({(left + 1, y - 2), (left + 1, y - 1)}), ivory)
    fill(small, both({(left + 1, y)}), ivory_shadow)
    fill(large, both(rect(left, y - 4, 2, 4) - {(left + 1, y - 4)}), ivory)
    fill(large, both({(left, y), (left + 1, y)}), ivory_shadow)
    save(small, "mouth/tusks_small.png")
    save(large, "mouth/tusks_large.png")


# Hair (tint: hair).

def cap(species, expand, max_y):
    x, y, w, h = GEOM[species]["head"]
    return rows(ellipse(x - expand, y - expand, w + 2 * expand, h + 2 * expand), 0, max_y)


def draw_hair():
    tones = gray_tones()

    def put(mask, name, texture=None, alpha=255):
        s = canvas()
        shade(s, mask, gray_tones(alpha))
        if texture:
            fill(s, {p for p in mask if texture(*p)}, gray(G_SHADOW, alpha))
        save(s, name)

    # Human back hair
    put(ellipse(16, 7, 32, 30) | polygon([(17, 20), (46, 20), (49, 50), (14, 50)]), "back_hair/long.png",
        texture=lambda x, y: y > 24 and x % 4 == 1)
    put(ellipse(17, 8, 30, 28) | rect(17, 20, 30, 20), "back_hair/shoulder.png",
        texture=lambda x, y: y > 26 and x % 5 == 2)

    # Human front hair
    fringe = {(x, 16) for x in range(0, SIZE, 3)}
    put((cap("human", 1, 16) - fringe) | both(rect(20, 16, 2, 8)), "front_hair/short.png")
    sweep = {p for p in ellipse(19, 9, 26, 32) if p[1] <= 21 - (p[0] - 19) * 0.4}
    put(cap("human", 2, 14) | sweep | rect(42, 14, 2, 6), "front_hair/side_part.png",
        texture=lambda x, y: (x + y) % 7 == 0)
    put(cap("human", 0, 15), "front_hair/buzz.png", texture=lambda x, y: (x + y) % 2 == 0, alpha=215)
    s = canvas()
    shade(s, cap("human", 0, 17), gray_tones(90), outline=False)
    shade(s, polygon([(29, 14), (30, 2), (33, 2), (34, 14)]), tones)
    save(s, "front_hair/mohawk.png")
    curly = rows(ellipse(15, 3, 34, 24), 0, 17) | both(rows(ellipse(14, 9, 10, 20), 0, 27))
    put(curly, "front_hair/curly.png", texture=lambda x, y: (x * 7 + y * 13) % 9 == 0)
    put(cap("human", 1, 15) | ellipse(27, 2, 10, 9), "front_hair/bun.png")

    # Muroth
    put(ellipse(10, 9, 44, 42), "back_hair/mane.png", texture=lambda x, y: (x * 3 + y) % 6 == 0)
    braid = rect(15, 26, 4, 24)
    put(both(braid), "back_hair/braids.png", texture=lambda x, y: y % 3 == 0)
    s = canvas()
    shade(s, ellipse(28, 6, 8, 9), tones)
    fill(s, rect(29, 14, 6, 2), gray(G_OUTLINE))
    save(s, "front_hair/topknot.png")

    # Vessari crests
    ridges = lambda x, y: y % 2 == 0  # noqa: E731
    put(polygon([(28, 14), (30, 0), (33, 0), (35, 14)]), "front_hair/crest_tall.png", texture=ridges)
    put(polygon([(27, 13), (33, 4), (47, 0), (38, 12)]), "front_hair/crest_swept.png", texture=ridges)
    put(both(polygon([(23, 14), (21, 2), (29, 10)])), "front_hair/crest_twin.png", texture=ridges)
    put(polygon([(29, 11), (31, 0), (32, 0), (34, 11)]) | both(polygon([(25, 13), (19, 4), (29, 10)])),
        "front_hair/crest_fan.png", texture=ridges)


def draw_facial_hair():
    tones = gray_tones()
    head = head_mask("human")
    y, left, right = GEOM["human"]["mouth"]
    mouth_hole = rect(left, y, right - left + 1, 2)

    s = canvas()
    beard = (rows(head, 30, 64) | rows({p for p in head if p[0] <= 23 or p[0] >= 40}, 24, 64)) - mouth_hole
    shade(s, beard, tones)
    save(s, "facial_hair/beard.png")

    s = canvas()
    shade(s, rect(left - 1, y - 2, right - left + 3, 2) | both({(left - 1, y), (left - 1, y + 1)}), tones)
    save(s, "facial_hair/mustache.png")

    s = canvas()
    shade(s, rect(30, y + 2, 4, 4) | rect(left, y + 2, right - left + 1, 1), tones)
    save(s, "facial_hair/goatee.png")

    s = canvas()
    fill(s, {p for p in rows(head, 29, 64) if (p[0] + p[1]) % 2 == 0} - mouth_hole, gray(G_SHADOW, 120))
    save(s, "facial_hair/stubble.png")


# Outfits (own colors) with accent parts (tint: accent).

BODY = rows(ellipse(4, 44, 56, 44), 0, SIZE - 1)
COLLAR_V = polygon([(26, 44), (37, 44), (31, 53), (32, 53)])


def draw_outfits():
    def outfit(name, color, draw_base, draw_accent, draw_detail=None):
        base, accent = canvas(), canvas()
        shade(base, BODY, color_tones(color))
        draw_base(base)
        draw_accent(accent)
        save(base, f"outfit/{name}.png")
        save(accent, f"outfit/{name}_accent.png")
        if draw_detail:
            detail = canvas()
            draw_detail(detail)
            save(detail, f"outfit/{name}_detail.png")

    def stripe(surface, low, high):
        band = rows(BODY, low, high)
        fill(surface, band, gray(245))
        fill(surface, rows(band, low, low) | rows(band, high, high), gray(180))

    miner = (168, 96, 46)

    def miner_base(s):
        fill(s, COLLAR_V & BODY, (58, 58, 62, 255))
        fill(s, both(rect(20, 46, 3, 18)) & BODY, (118, 66, 32, 255))
        shade(s, rect(36, 57, 6, 4), color_tones((150, 84, 40)))

    outfit("miner", miner, miner_base, lambda s: stripe(s, 55, 57))

    def foreman_base(s):
        fill(s, both(polygon([(26, 44), (31, 57), (21, 50)])) & BODY, (60, 68, 80, 255))
        fill(s, polygon([(27, 44), (36, 44), (31, 51), (32, 51)]), (228, 228, 222, 255))

    def foreman_accent(s):
        shade(s, both(ellipse(8, 50, 10, 5)) & BODY, gray_tones())
        shade(s, rect(40, 56, 3, 3), gray_tones(), outline=False)

    outfit("foreman", (86, 96, 112), foreman_base, foreman_accent)

    def dock_base(s):
        fill(s, rect(27, 44, 10, 2) & BODY, (46, 58, 52, 255))

    vest = both(polygon([(9, 52), (24, 46), (26, 64), (7, 64)])) & BODY

    def dock_accent(s):
        shade(s, vest, gray_tones())

    def dock_detail(s):
        fill(s, rows(vest, 58, 59), (236, 238, 232, 255))

    outfit("dockworker", (70, 86, 78), dock_base, dock_accent, dock_detail)

    def security_base(s):
        shade(s, polygon([(22, 50), (41, 50), (39, 63), (24, 63)]), color_tones((66, 78, 104)))
        shade(s, rect(26, 40, 12, 6), color_tones((50, 60, 84)))

    def security_accent(s):
        shade(s, both(ellipse(3, 46, 17, 11)), gray_tones())

    outfit("security", (44, 54, 76), security_base, security_accent)

    def politician_base(s):
        fill(s, polygon([(26, 44), (37, 44), (32, 57), (31, 57)]), (232, 232, 228, 255))
        fill(s, both(line((26, 44), (30, 57), 2)) & BODY, (26, 26, 34, 255))

    def politician_accent(s):
        shade(s, polygon([(30, 45), (33, 45), (34, 55), (32, 58), (31, 58), (29, 55)]), gray_tones())
        fill(s, rect(40, 52, 4, 2), gray(250))

    outfit("politician", (40, 40, 52), politician_base, politician_accent)

    def default_base(s):
        fill(s, COLLAR_V & BODY, (70, 72, 84, 255))

    def default_accent(s):
        fill(s, (rows(BODY, 44, 45) | rect(31, 46, 2, 18)) - COLLAR_V, gray(230))

    outfit("default", (104, 108, 122), default_base, default_accent)


# Accessories, one file per species.

def draw_accessories():
    for species, g in GEOM.items():
        hx, hy, hw, hh = g["head"]
        ex, ew, ey, eh = g["eye"]
        forehead = g["forehead"]
        mouth_y, _, mouth_right = g["mouth"]
        left_eye_cx = ex + ew // 2
        right_eye_cx = SIZE - 1 - left_eye_cx
        ear_x, ear_y = g["ear"]

        s = canvas()
        fill(s, rect(hx - 1, forehead - 1, hw + 2, 2), (70, 52, 40, 255))
        for cx in (left_eye_cx, right_eye_cx):
            lens = ellipse(cx - 3, forehead - 4, 7, 7)
            fill(s, lens, (98, 98, 106, 255))
            fill(s, ellipse(cx - 2, forehead - 3, 5, 5), (84, 170, 190, 255))
            fill(s, {(cx - 1, forehead - 2)}, (210, 245, 250, 255))
        save(s, f"accessory/goggles_{species}.png")

        if g["lobe"]:
            s = canvas()
            lx, ly = g["lobe"]
            fill(s, {(lx, ly), (lx, ly + 1)}, (230, 186, 70, 255))
            fill(s, {(lx, ly + 1)}, (160, 120, 40, 255))
            save(s, f"accessory/earring_{species}.png")

        s = canvas()
        scar_x = right_eye_cx + 1
        cut = line((scar_x, ey - 3), (scar_x + 2, g["cheek_y"] + 3))
        fill(s, {(x + 1, y) for x, y in cut}, gray(248))
        fill(s, cut, gray(140))
        save(s, f"accessory/scar_{species}.png")

        s = canvas()
        fill(s, line((hx, ey + 2), (SIZE - hx, forehead - 2)), (40, 36, 34, 255))
        shade(s, ellipse(ex - 1, ey - 1, ew + 2, eh + 3), color_tones((34, 30, 32)))
        save(s, f"accessory/eyepatch_{species}.png")

        s = canvas()
        right_ex = SIZE - ex - ew
        shade(s, rect(right_ex - 2, ey - 2, ew + 4, eh + 4), color_tones((150, 156, 168)))
        fill(s, rect(right_eye_cx, ey, 2, 2), (230, 60, 60, 255))
        fill(s, {(right_eye_cx, ey)}, (255, 170, 170, 255))
        save(s, f"accessory/cybereye_{species}.png")

        s = canvas()
        rx = SIZE - 1 - ear_x
        fill(s, line((rx - 1, ear_y + 4), (mouth_right + 3, mouth_y)), (92, 96, 106, 255))
        shade(s, rect(rx - 1, ear_y - 1, 3, 6), color_tones((60, 64, 74)))
        fill(s, rect(mouth_right + 2, mouth_y - 1, 2, 2), (60, 64, 72, 255))
        save(s, f"accessory/earpiece_{species}.png")


def generate():
    pygame.init()
    draw_heads()
    draw_eyes()
    draw_mouths()
    draw_hair()
    draw_facial_hair()
    draw_outfits()
    draw_accessories()


def contact_sheet(path, columns=8, rows_=4, seed=7):
    sys.path.insert(0, str(SPACE / "src"))
    from entities.npcs.portrait import compose, roll_appearance
    from entities.npcs.species import SPECIES

    rng = random.Random(seed)
    jobs = ["Miner", "Foreman", "Dockworker", "Security", "Politician", "Bartender"]
    guilds = ["assembly", "caravaneers", "cohort", "dominion"]
    cell = SIZE * 2 + 8
    sheet = pygame.Surface((columns * cell + 8, rows_ * cell + 8))
    sheet.fill((12, 14, 26))
    species_ids = list(SPECIES)
    for i in range(columns * rows_):
        species = species_ids[i % len(species_ids)]
        recipe = roll_appearance(f"sheet/{seed}/{i}", species, rng.choice(jobs), rng.choice(guilds))
        x, y = 8 + (i % columns) * cell, 8 + (i // columns) * cell
        pygame.draw.rect(sheet, (28, 34, 58), (x, y, SIZE * 2, SIZE * 2))
        sheet.blit(pygame.transform.scale(compose(recipe), (SIZE * 2, SIZE * 2)), (x, y))
    pygame.image.save(sheet, str(path))


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--preview", help="also write a contact sheet of rolled portraits to this PNG")
    args = parser.parse_args()
    generate()
    print(f"Wrote placeholder layers to {OUT}")
    if args.preview:
        contact_sheet(args.preview)
        print(f"Wrote contact sheet to {args.preview}")


if __name__ == "__main__":
    main()
