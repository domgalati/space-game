"""Room furnishing helpers shared by themes."""
from ..tiles import STAMPS

OPPOSITE = {"N": "S", "S": "N", "E": "W", "W": "E"}


def flush(room, side, stamp_name, offset=0):
    """Top-left cell that puts a stamp flush against one wall of a room, centered plus offset."""
    stamp = STAMPS[stamp_name]
    r = room.rect
    x = min(max(r.cx - stamp.width // 2 + offset, r.x), r.right - stamp.width)
    y = min(max(r.cy - stamp.height // 2 + offset, r.y), r.bottom - stamp.height)
    if side == "N":
        return x, r.y
    if side == "S":
        return x, r.bottom - stamp.height
    if side == "W":
        return r.x, y
    return r.right - stamp.width, y


def along_walls(grid, room, names, count, keep_clear, sides=("N", "S", "E", "W"), attempts=60):
    """Scatter stamps flush against the given walls, never blocking doors or reachability."""
    placed = 0
    r = room.rect
    for _ in range(count):
        for _ in range(attempts):
            name = grid.rng.choice(names)
            stamp = STAMPS[name]
            side = grid.rng.choice(sides)
            if side in ("N", "S"):
                x = grid.rng.randint(r.x, r.right - stamp.width)
                y = r.y if side == "N" else r.bottom - stamp.height
            else:
                y = grid.rng.randint(r.y, r.bottom - stamp.height)
                x = r.x if side == "W" else r.right - stamp.width
            if grid.place(name, x, y, keep_clear):
                placed += 1
                break
    return placed


def front_of(room, side, x, y, height=1, width=1):
    """The floor cell a player stands on to use a stamp placed flush against `side`."""
    if side == "N":
        return x + width // 2, y + height
    if side == "S":
        return x + width // 2, y - 1
    if side == "W":
        return x + width, y + height // 2
    return x - 1, y + height // 2


def add_posts(grid, job, cells):
    for cell in cells:
        if grid.walkable(cell):
            grid.posts.append((job, *cell))
