"""Planet surfaces: walled compounds on open ground, joined by paths, with scattered terrain."""
from ..grid import Grid, Rect
from ..tiles import extra
from . import station

# floors: style -> (main, variant, variant chance), layered over station.FLOORS.
# terrain: scattered outside city limits (everywhere when there are none).
# clutter + city_margin: pave a box around the compounds and dress it with street props.
PALETTES = {
    "badlands": {
        "floors": {
            "ground": ("floor_ground", "floor_ground_b", 0.35),
            "path": ("floor_path", "floor_path", 0.0),
        },
        "terrain": {
            "crater": 0.0015,
            "rock_orange": 0.002,
            "rock_white": 0.001,
            "shrub_a": 0.003,
            "shrub_b": 0.003,
            "shrub_c": 0.002,
        },
    },
    "urban": {
        "floors": {
            "ground": ("floor_rock", "floor_rock_b", 0.4),
            "pavement": ("floor_concrete", "floor_concrete_b", 0.12),
            "path": ("floor_road", "floor_road_b", 0.15),
            "housing": ("floor_tile", "floor_tile_b", 0.2),
        },
        "terrain": {
            "rock_white": 0.004,
            "rock_blue": 0.004,
        },
        "clutter": {
            "antenna": 0.0002,
            "terminal_c": 0.0006,
            "bot_a": 0.0004,
            "bot_c": 0.0004,
            "fuel_tanks": 0.0002,
        },
        "city_margin": 8,
    },
}


def generate(spec, rng):
    palette = PALETTES[spec.get("palette", "badlands")]
    width, height = spec["size"]
    grid = Grid(width, height, rng)
    grid.carve(Rect(1, 1, width - 2, height - 2), "ground")

    kinds = []
    for entry in spec["rooms"]:
        kinds += [entry["type"]] * entry.get("count", 1)

    compounds = []
    area = Rect(4, 4, width - 8, height - 8)
    for kind in kinds:
        (min_w, max_w), (min_h, max_h) = station.ROOM_SIZE.get(kind, station.DEFAULT_SIZE)
        for _ in range(200):
            rect = Rect(0, 0, rng.randint(min_w, max_w), rng.randint(min_h, max_h))
            rect.x = rng.randint(area.x, area.right - rect.w)
            rect.y = rng.randint(area.y, area.bottom - rect.h)
            if not any(rect.inflate(5).overlaps(other.rect) for other in compounds):
                compounds.append(_compound(grid, kind, rect))
                break

    center = (width // 2, height // 2)
    for room in compounds:
        _path(grid, room.approach, center)

    city = _pave_city(grid, compounds, palette["city_margin"]) if "city_margin" in palette else None

    for room in compounds:
        station.FURNISH.get(room.kind, station._furnish_generic)(grid, room)

    keep_clear = set()
    for room in compounds:
        keep_clear |= grid.room_keep_clear(room, margin=3)
        keep_clear |= set(room.rect.cells())
    _scatter(grid, palette["terrain"], keep_clear, lambda cell: city is None or not city.contains(*cell))
    if city:
        roads = {cell for cell, style in grid.floor.items() if style == "path"}
        _scatter(grid, palette["clutter"], keep_clear | roads, lambda cell: city.contains(*cell), check=True)

    return grid, _background(grid, palette)


def _scatter(grid, densities, keep_clear, allowed, check=False):
    rng = grid.rng
    for name, density in densities.items():
        for _ in range(int(grid.width * grid.height * density)):
            x, y = rng.randint(2, grid.width - 4), rng.randint(2, grid.height - 4)
            if allowed((x, y)):
                grid.place(name, x, y, keep_clear, check=check)


def _pave_city(grid, compounds, margin):
    """Open ground within `margin` of the compounds' bounding box becomes pavement."""
    x0 = max(1, min(r.rect.x for r in compounds) - margin)
    y0 = max(1, min(r.rect.y for r in compounds) - margin)
    x1 = min(grid.width - 1, max(r.rect.right for r in compounds) + margin)
    y1 = min(grid.height - 1, max(r.rect.bottom for r in compounds) + margin)
    city = Rect(x0, y0, x1 - x0, y1 - y0)
    for cell in city.cells():
        if grid.floor.get(cell) == "ground":
            grid.floor[cell] = "pavement"
    return city


def _compound(grid, kind, rect):
    room = grid.add_room(kind, rect, station.ROOM_FLOOR.get(kind, "plaza"))
    cx, cy = grid.width // 2, grid.height // 2
    dx, dy = cx - rect.cx, cy - rect.cy
    side = ("E" if dx > 0 else "W") if abs(dx) > abs(dy) else ("S" if dy > 0 else "N")
    room.door_side = side

    if side in ("N", "S"):
        wall_y = rect.y - 1 if side == "N" else rect.bottom
        gaps = [(x, wall_y) for x in range(rect.cx - 1, rect.cx + 2)]
        room.doors = [(x, rect.y if side == "N" else rect.bottom - 1) for x, _ in gaps]
        room.approach = (rect.cx, wall_y - 1 if side == "N" else wall_y + 1)
    else:
        wall_x = rect.x - 1 if side == "W" else rect.right
        gaps = [(wall_x, y) for y in range(rect.cy - 1, rect.cy + 2)]
        room.doors = [(rect.x if side == "W" else rect.right - 1, y) for _, y in gaps]
        room.approach = (wall_x - 1 if side == "W" else wall_x + 1, rect.cy)

    grid.add_wall_ring(rect, gaps)
    for cell in gaps:
        grid.floor[cell] = room.floor
        grid.decor[cell] = extra("door_h" if side in ("N", "S") else "door_v")
    return room


def _path(grid, start, end):
    """Two-wide L-shaped path, drawn only over open ground."""
    (x0, y0), (x1, y1) = start, end
    cells = [(x, y0) for x in range(min(x0, x1), max(x0, x1) + 1)]
    cells += [(x1, y) for y in range(min(y0, y1), max(y0, y1) + 1)]
    for x, y in cells:
        for cell in ((x, y), (x + 1, y), (x, y + 1)):
            if grid.floor.get(cell) == "ground" and cell not in grid.decor:
                grid.floor[cell] = "path"


def _background(grid, palette):
    rng = grid.rng
    floors = {**station.FLOORS, **palette["floors"]}
    cells = {}
    for cell, style in grid.floor.items():
        main, variant, chance = floors.get(style, floors["ground"])
        cells[cell] = extra(variant if rng.random() < chance else main)
    return cells
