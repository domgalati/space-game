"""Tilesets the generated maps reference, and multi-tile prop stamps cut from the packs."""
from . import extras

# Same sources and firstgids as Terramonta.tmx, so gids mean the same thing in every map.
TILESETS = [
    ("TilesetSpriteSheet3x-tilesize-24.tsx", 1),
    ("2FrameAnimTilesetSpriteSheetx3-tilesize24.tsx", 334),
    ("mine_machine_sheet.tsx", 360),
    ("computor.tsx", 362),
    ("RoguelikeAllSpriteSheet3x-tilesize24.tsx", 364),
    ("SpaceRoguelikeSpriteSheet3x-tilesize-24.tsx", 1100),
    ("RoguelikeOverSpriteSheet3x-tilesize-24.tsx", 1951),
    ("mapgen_extras.tsx", 5175),
    ("mapgen_palettes.tsx", 6000),
]
EXTRAS_FIRSTGID = 5175
PALETTES_FIRSTGID = 6000

_PACKS = "space/assets/Downloaded Packs"
SHEET_FILES = {
    "tileset": f"{_PACKS}/MAS Space Roguelike (v.1.0)/TilesetSpriteSheet3x-tilesize-24.png",
    "space": f"{_PACKS}/MAS Space Roguelike (v.1.0)/SpaceRoguelikeSpriteSheet3x-tilesize-24.png",
    "roguelike": f"{_PACKS}/MAS Roguelike (v.1.01)/RoguelikeAllSpriteSheet3x-tilesize24.png",
}


def extra(name):
    if name in extras.PALETTE_INDEX:
        return PALETTES_FIRSTGID + extras.PALETTE_INDEX[name]
    return EXTRAS_FIRSTGID + extras.INDEX[name]


class Stamp:
    """A rectangular block of pack tiles placed as one solid prop.

    The block is copied into the extras sheet with its black backdrop keyed out,
    so props sit on any floor instead of in a black box.
    """

    def __init__(self, sheet, row, col, width, height):
        self.sheet = sheet
        self.source = (col * extras.TILE, row * extras.TILE, width * extras.TILE, height * extras.TILE)
        self.width = width
        self.height = height
        self.tiles = []


STAMPS = {
    "console": Stamp("tileset", 7, 6, 3, 3),
    "cabinets": Stamp("tileset", 13, 0, 3, 3),
    "lander": Stamp("tileset", 16, 0, 3, 3),
    "lander_hot": Stamp("tileset", 16, 3, 3, 3),
    "hatch": Stamp("tileset", 25, 1, 3, 3),
    "locker": Stamp("tileset", 5, 3, 2, 2),
    "control_panel": Stamp("tileset", 5, 7, 2, 2),
    "servitor": Stamp("tileset", 7, 0, 2, 3),
    "jukebox": Stamp("tileset", 7, 2, 2, 3),
    "fuel_tanks": Stamp("tileset", 10, 2, 2, 3),
    "pillars": Stamp("tileset", 10, 4, 2, 3),
    "antenna": Stamp("tileset", 10, 6, 3, 3),
    "dome": Stamp("tileset", 13, 5, 4, 3),
    "bot_a": Stamp("tileset", 2, 0, 1, 1),
    "bot_b": Stamp("tileset", 2, 1, 1, 1),
    "bot_c": Stamp("tileset", 2, 2, 1, 1),
    "terminal": Stamp("space", 6, 19, 1, 1),
    "terminal_b": Stamp("space", 6, 20, 1, 1),
    "terminal_c": Stamp("space", 6, 21, 1, 1),
    "bar_front": Stamp("roguelike", 10, 3, 3, 2),
    "shelf": Stamp("roguelike", 31, 5, 1, 1),
    "table": Stamp("roguelike", 31, 8, 1, 1),
    "chair": Stamp("roguelike", 31, 7, 1, 1),
    "chest": Stamp("roguelike", 31, 6, 1, 1),
    "sack_blue": Stamp("roguelike", 29, 4, 1, 1),
    "sack_gold": Stamp("roguelike", 29, 5, 1, 1),
    "crater": Stamp("tileset", 21, 0, 2, 2),
    "rock_white": Stamp("tileset", 21, 5, 2, 2),
    "rock_gold": Stamp("tileset", 21, 7, 2, 2),
    "rock_orange": Stamp("tileset", 23, 5, 2, 2),
    "rock_blue": Stamp("tileset", 23, 7, 2, 2),
    "shrub_a": Stamp("tileset", 23, 0, 1, 1),
    "shrub_b": Stamp("tileset", 23, 2, 1, 1),
    "shrub_c": Stamp("tileset", 24, 3, 1, 1),
    # New stamps go last so gids in already generated maps stay valid.
    "bed_white": Stamp("roguelike", 6, 0, 2, 2),
    "bed_orange": Stamp("roguelike", 6, 2, 2, 2),
    "bed_green": Stamp("roguelike", 6, 4, 2, 2),
}

_next = len(extras.NAMES)
for _stamp in STAMPS.values():
    _stamp.tiles = [
        [EXTRAS_FIRSTGID + _next + dy * _stamp.width + dx for dx in range(_stamp.width)]
        for dy in range(_stamp.height)
    ]
    _next += _stamp.width * _stamp.height
assert EXTRAS_FIRSTGID + _next <= PALETTES_FIRSTGID, "mapgen_extras has outgrown its gid range"


def prop_blocks():
    """(sheet png, source rect, width, height) for every stamp, in extras-sheet order."""
    return [(SHEET_FILES[s.sheet], s.source, s.width, s.height) for s in STAMPS.values()]
