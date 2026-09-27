"""Planet surfaces: walled compounds on open ground, joined by paths, with scattered terrain."""
from ..grid import Grid, Rect
from ..tiles import extra
from . import station

FLOORS = dict(station.FLOORS)
FLOORS["ground"] = ("floor_ground", "floor_ground_b", 0.35)
FLOORS["path"] = ("floor_path", "floor_path", 0.0)

TERRAIN = {
    "crater": 0.0015,
    "rock_orange": 0.002,
    "rock_white": 0.001,
    "shrub_a": 0.003,
    "shrub_b": 0.003,
    "shrub_c": 0.002,
}


def generate(spec, rng):
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

    for room in compounds:
        station.FURNISH.get(room.kind, station._furnish_generic)(grid, room)

    keep_clear = set()
    for room in compounds:
        keep_clear |= grid.room_keep_clear(room, margin=3)
    for name, density in TERRAIN.items():
        for _ in range(int(width * height * density)):
            x, y = rng.randint(2, width - 4), rng.randint(2, height - 4)
            grid.place(name, x, y, keep_clear, check=False)

    return grid, _background(grid)


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
    """Two-wide L-shaped dirt path, drawn only over open ground."""
    (x0, y0), (x1, y1) = start, end
    cells = [(x, y0) for x in range(min(x0, x1), max(x0, x1) + 1)]
    cells += [(x1, y) for y in range(min(y0, y1), max(y0, y1) + 1)]
    for x, y in cells:
        for cell in ((x, y), (x + 1, y), (x, y + 1)):
            if grid.floor.get(cell) == "ground" and cell not in grid.decor:
                grid.floor[cell] = "path"


def _background(grid):
    rng = grid.rng
    cells = {}
    for cell, style in grid.floor.items():
        main, variant, chance = FLOORS.get(style, FLOORS["ground"])
        cells[cell] = extra(variant if rng.random() < chance else main)
    return cells
