"""Procedurally drawn tiles (walls, floors, stars) in the MAS pack palette.

Everything is drawn as 8x8 pixel art and scaled 3x so it matches the 24px pack tiles.
"""
import pygame

ART = 8
SCALE = 3
TILE = ART * SCALE
COLUMNS = 8

BLACK = (4, 3, 3)
NIGHT = (28, 22, 24)
DUSK = (71, 65, 107)
LAVENDER = (138, 143, 196)
WHITE = (249, 245, 239)
GREEN = (108, 140, 80)
RED = (161, 61, 59)
MAROON = (78, 40, 46)
YELLOW = (240, 212, 114)
HULL = (14, 11, 13)

N, E, S, W = 1, 2, 4, 8

# Offsets across a wall band, from its outer to inner edge.
_BAND = (LAVENDER, WHITE, LAVENDER, DUSK)


def _wall(mask):
    def draw(put):
        straight = mask in (N | S, E | W)
        if mask & (E | W) or mask == 0:
            x0 = 0 if mask & W or mask == 0 else 2
            x1 = ART if mask & E or mask == 0 else 6
            for i, color in enumerate(_BAND):
                for x in range(x0, x1):
                    put(x, 2 + i, color)
        if mask & (N | S):
            y0 = 0 if mask & N else 2
            y1 = ART if mask & S else 6
            for i, color in enumerate(_BAND):
                for y in range(y0, y1):
                    put(2 + i, y, color)
        if not straight:
            for x in range(1, 7):
                for y in range(1, 7):
                    edge = x in (1, 6) or y in (1, 6)
                    put(x, y, LAVENDER if edge else DUSK)
            for x in (3, 4):
                for y in (3, 4):
                    put(x, y, GREEN)
            put(1, 1, WHITE)
    return draw


def _fill(color):
    def draw(put):
        for x in range(ART):
            for y in range(ART):
                put(x, y, color)
    return draw


def _layers(*draws):
    def draw(put):
        for d in draws:
            d(put)
    return draw


def _pixels(color, points):
    def draw(put):
        for x, y in points:
            put(x, y, color)
    return draw


def _hazard(put):
    for x in range(ART):
        for y in range(ART):
            put(x, y, YELLOW if ((x + y) // 2) % 2 == 0 else BLACK)


def _planks(joint_top, joint_bottom):
    def draw(put):
        _fill(MAROON)(put)
        for x in range(ART):
            put(x, 3, NIGHT)
            put(x, 7, NIGHT)
            put(x, 0, (104, 52, 54))
        for y in range(0, 3):
            put(joint_top, y, NIGHT)
        for y in range(4, 7):
            put(joint_bottom, y, NIGHT)
    return draw


def _hull(put):
    _fill(HULL)(put)
    for x in range(ART):
        for y in range(ART):
            if (x - y) % 4 == 0:
                put(x, y, NIGHT)


def _door(horizontal):
    def draw(put):
        _fill(BLACK)(put)
        for i in range(ART):
            color = YELLOW if (i // 2) % 2 == 0 else NIGHT
            if horizontal:
                put(i, 3, color)
                put(i, 4, color)
            else:
                put(3, i, color)
                put(4, i, color)
    return draw


def _star(color, x, y, twinkle=False):
    def draw(put):
        put(x, y, color)
        if twinkle:
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                put(x + dx, y + dy, DUSK)
    return draw


TILES = {}
for _mask in range(16):
    TILES[f"wall_{_mask}"] = _wall(_mask)

TILES.update({
    "floor_corridor": _layers(_fill(BLACK), _pixels(DUSK, [(0, 0)])),
    "floor_corridor_b": _layers(_fill(BLACK), _pixels(DUSK, [(0, 0)]), _pixels(NIGHT, [(4, 5), (5, 5)])),
    "floor_plaza": _layers(_fill(NIGHT), _pixels(DUSK, [(i, 0) for i in range(ART)] + [(0, i) for i in range(ART)])),
    "floor_plaza_b": _layers(
        _fill(NIGHT),
        _pixels(DUSK, [(i, 0) for i in range(ART)] + [(0, i) for i in range(ART)]),
        _pixels(LAVENDER, [(4, 4)]),
    ),
    "floor_bay": _layers(_fill(BLACK), _pixels(NIGHT, [(i, 0) for i in range(ART)] + [(0, i) for i in range(ART)]),
                         _pixels(DUSK, [(3, 3), (4, 4)])),
    "floor_bay_b": _layers(_fill(BLACK), _pixels(NIGHT, [(i, 0) for i in range(ART)] + [(0, i) for i in range(ART)])),
    "floor_hazard": _hazard,
    "floor_cantina": _planks(2, 6),
    "floor_cantina_b": _planks(5, 1),
    "floor_command": _layers(_fill(NIGHT), _pixels(DUSK, [(0, 0), (7, 0), (0, 7), (7, 7), (3, 3), (4, 4), (3, 4), (4, 3)])),
    "floor_command_b": _layers(_fill(NIGHT), _pixels(DUSK, [(0, 0), (7, 0), (0, 7), (7, 7)]), _pixels(LAVENDER, [(3, 3)])),
    "floor_ground": _layers(_fill(BLACK), _pixels(MAROON, [(2, 5)])),
    "floor_ground_b": _layers(_fill(BLACK), _pixels(MAROON, [(6, 1), (1, 6)])),
    "floor_path": _layers(_fill(NIGHT), _pixels(MAROON, [(1, 2), (5, 6), (6, 1)])),
    "door_h": _door(True),
    "door_v": _door(False),
    "hull": _hull,
    "star_1": _star(WHITE, 3, 4),
    "star_2": _star(LAVENDER, 6, 1),
    "star_3": _star(DUSK, 1, 6),
    "star_4": _star(WHITE, 4, 3, twinkle=True),
    "star_5": _star((154, 64, 126), 2, 2),
    "star_6": _star(LAVENDER, 5, 5),
})

NAMES = list(TILES)
INDEX = {name: i for i, name in enumerate(NAMES)}


def _key_backdrop(block):
    """Clear the near-black backdrop reachable from the block's edges; inner outlines stay."""
    w, h = block.get_size()

    def dark(p):
        color = block.get_at(p)
        return color.a and color.r + color.g + color.b <= 30

    stack = [(x, y) for x in range(w) for y in (0, h - 1)] + [(x, y) for y in range(h) for x in (0, w - 1)]
    seen = set()
    while stack:
        p = stack.pop()
        if p in seen or not (0 <= p[0] < w and 0 <= p[1] < h) or not dark(p):
            continue
        seen.add(p)
        block.set_at(p, (0, 0, 0, 0))
        x, y = p
        stack += [(x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)]
    return block


def build_sheet(prop_blocks, load_image):
    """Drawn tiles first, then keyed copies of every prop block (row-major, COLUMNS wide)."""
    tiles = []
    for name in NAMES:
        art = pygame.Surface((ART, ART), pygame.SRCALPHA)

        def put(x, y, color, art=art):
            if 0 <= x < ART and 0 <= y < ART:
                art.set_at((x, y), color)

        TILES[name](put)
        tiles.append(pygame.transform.scale(art, (TILE, TILE)))

    sources = {}
    for path, rect, width, height in prop_blocks:
        if path not in sources:
            sources[path] = load_image(path)
        block = _key_backdrop(sources[path].subsurface(rect).copy())
        for dy in range(height):
            for dx in range(width):
                tiles.append(block.subsurface((dx * TILE, dy * TILE, TILE, TILE)).copy())

    rows = (len(tiles) + COLUMNS - 1) // COLUMNS
    sheet = pygame.Surface((COLUMNS * TILE, rows * TILE), pygame.SRCALPHA)
    for i, tile in enumerate(tiles):
        sheet.blit(tile, ((i % COLUMNS) * TILE, (i // COLUMNS) * TILE))
    return sheet, len(tiles)


def write_tileset(png_path, tsx_path, image_source, prop_blocks, load_image):
    sheet, count = build_sheet(prop_blocks, load_image)
    pygame.image.save(sheet, png_path)
    tsx = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<tileset version="1.10" tiledversion="1.10.2" name="mapgen_extras" tilewidth="{TILE}" '
        f'tileheight="{TILE}" tilecount="{count}" columns="{COLUMNS}">\n'
        f' <image source="{image_source}" width="{sheet.get_width()}" height="{sheet.get_height()}"/>\n'
        '</tileset>\n'
    )
    with open(tsx_path, "w", encoding="utf-8") as file:
        file.write(tsx)
