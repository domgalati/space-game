"""Space station interiors: a market hub inside a ring corridor, rooms docked around the rim."""
from ..grid import Grid, Rect
from ..tiles import extra
from .common import OPPOSITE, add_posts, along_walls, flush, front_of

MARGIN = 3  # open space kept around the hull
RING_WIDTH = 3
CORRIDOR_WIDTH = 3
STAR_DENSITY = 0.05

FLOORS = {
    "corridor": ("floor_corridor", "floor_corridor_b", 0.12),
    "plaza": ("floor_plaza", "floor_plaza_b", 0.2),
    "bay": ("floor_bay", "floor_bay_b", 0.5),
    "cantina": ("floor_cantina", "floor_cantina_b", 0.5),
    "command": ("floor_command", "floor_command_b", 0.25),
    "housing": ("floor_cantina", "floor_cantina_b", 0.5),
}
STARS = ["star_1", "star_2", "star_3", "star_3", "star_4", "star_5", "star_6", "star_6"]

ROOM_FLOOR = {"docking_bay": "bay", "cantina": "cantina", "command": "command", "market": "plaza", "housing": "housing"}
# (min_w, max_w), (min_h, max_h)
ROOM_SIZE = {
    "docking_bay": ((15, 18), (11, 13)),
    "cantina": ((12, 15), (8, 10)),
    "command": ((13, 16), (8, 10)),
    "housing": ((12, 15), (8, 10)),
}
DEFAULT_SIZE = ((10, 13), (7, 9))


def generate(spec, rng):
    width, height = spec["size"]
    grid = Grid(width, height, rng)

    hub_rect = Rect(0, 0, rng.randint(18, 22), rng.randint(10, 12))
    hub_rect.x, hub_rect.y = (width - hub_rect.w) // 2, (height - hub_rect.h) // 2
    hub_kind = next((r["type"] for r in spec["rooms"] if r.get("at") == "hub"), "market")
    hub = grid.add_room(hub_kind, hub_rect, ROOM_FLOOR.get(hub_kind, "plaza"))

    gap_x, gap_y = rng.randint(5, 7), rng.randint(4, 5)
    ring = Rect(hub_rect.x - gap_x - RING_WIDTH, hub_rect.y - gap_y - RING_WIDTH,
                hub_rect.w + 2 * (gap_x + RING_WIDTH), hub_rect.h + 2 * (gap_y + RING_WIDTH))
    for band in (Rect(ring.x, ring.y, ring.w, RING_WIDTH),
                 Rect(ring.x, ring.bottom - RING_WIDTH, ring.w, RING_WIDTH),
                 Rect(ring.x, ring.y, RING_WIDTH, ring.h),
                 Rect(ring.right - RING_WIDTH, ring.y, RING_WIDTH, ring.h)):
        grid.carve(band, "corridor")

    _spokes(grid, hub, ring)
    outer = _outer_rooms(grid, spec, ring)

    for room in [hub] + outer:
        FURNISH.get(room.kind, _furnish_generic)(grid, room)
    _dress_ring(grid, ring, [hub] + outer)

    grid.derive_walls()
    background = _background(grid)
    return grid, background


# ---- layout ---------------------------------------------------------------------

def _door_decor(grid, cells, horizontal_passage):
    for cell in cells:
        grid.decor[cell] = extra("door_v" if horizontal_passage else "door_h")


def _spokes(grid, hub, ring):
    r, h = ring, hub.rect
    inner_top, inner_bottom = r.y + RING_WIDTH, r.bottom - RING_WIDTH
    inner_left, inner_right = r.x + RING_WIDTH, r.right - RING_WIDTH
    x_n = h.cx - 1 + grid.rng.randint(-3, 3)
    x_s = h.cx - 1 + grid.rng.randint(-3, 3)
    y_w = h.cy - 1 + grid.rng.randint(-2, 2)
    y_e = h.cy - 1 + grid.rng.randint(-2, 2)
    spokes = [
        (Rect(x_n, inner_top, CORRIDOR_WIDTH, h.y - inner_top), "N"),
        (Rect(x_s, h.bottom, CORRIDOR_WIDTH, inner_bottom - h.bottom), "S"),
        (Rect(inner_left, y_w, h.x - inner_left, CORRIDOR_WIDTH), "W"),
        (Rect(h.right, y_e, inner_right - h.right, CORRIDOR_WIDTH), "E"),
    ]
    for rect, side in spokes:
        grid.carve(rect, "corridor")
        if side == "N":
            hub.doors += [(x, h.y) for x in range(rect.x, rect.right)]
            _door_decor(grid, [(x, rect.bottom - 1) for x in range(rect.x, rect.right)], False)
        elif side == "S":
            hub.doors += [(x, h.bottom - 1) for x in range(rect.x, rect.right)]
            _door_decor(grid, [(x, rect.y) for x in range(rect.x, rect.right)], False)
        elif side == "W":
            hub.doors += [(h.x, y) for y in range(rect.y, rect.bottom)]
            _door_decor(grid, [(rect.right - 1, y) for y in range(rect.y, rect.bottom)], True)
        else:
            hub.doors += [(h.right - 1, y) for y in range(rect.y, rect.bottom)]
            _door_decor(grid, [(rect.x, y) for y in range(rect.y, rect.bottom)], True)


def _assign_sides(rng, kinds):
    """Docking bays take the long east/west arms; everything else fills the remaining sides."""
    bays = [k for k in kinds if k == "docking_bay"]
    others = [k for k in kinds if k != "docking_bay"]
    arms = ["W", "E"]
    rng.shuffle(arms)
    sides = {"N": [], "S": [], "W": [], "E": []}
    for i, kind in enumerate(bays):
        sides[arms[i % 2]].append(kind)
    rest = [s for s in ("N", "S", "W", "E") if not sides[s]] or ["N", "S"]
    rng.shuffle(rest)
    for i, kind in enumerate(others):
        sides[rest[i % len(rest)]].append(kind)
    return sides


def _outer_rooms(grid, spec, ring):
    rng = grid.rng
    kinds = []
    for entry in spec["rooms"]:
        if entry.get("at") == "hub":
            continue
        kinds += [entry["type"]] * entry.get("count", 1)

    rooms = []
    for side, side_kinds in _assign_sides(rng, kinds).items():
        slots = len(side_kinds)
        for slot, kind in enumerate(side_kinds):
            (min_w, max_w), (min_h, max_h) = ROOM_SIZE.get(kind, DEFAULT_SIZE)
            conn = rng.randint(2, 4)
            if side in ("N", "S"):
                span = (ring.w - 2 * (slots - 1)) // slots
                w = min(rng.randint(min_w, max_w), span)
                room_space = (ring.y - MARGIN - 1 - conn) if side == "N" else (grid.height - MARGIN - 1 - ring.bottom - conn)
                h = min(rng.randint(min_h, max_h), room_space)
                lo = ring.x + slot * (span + 2)
                x = rng.randint(lo, lo + span - w)
                y = ring.y - conn - h if side == "N" else ring.bottom + conn
            else:
                span = (grid.height - 2 * (MARGIN + 1) - 2 * (slots - 1)) // slots
                h = min(rng.randint(min_h, max_h), span)
                room_space = (ring.x - MARGIN - 1 - conn) if side == "W" else (grid.width - MARGIN - 1 - ring.right - conn)
                w = min(rng.randint(min_w, max_w), room_space)
                lo = MARGIN + 1 + slot * (span + 2)
                if slots == 1:
                    y = max(lo, min(ring.cy - h // 2 + rng.randint(-3, 3), lo + span - h))
                else:
                    y = rng.randint(lo, lo + span - h)
                x = ring.x - conn - w if side == "W" else ring.right + conn
            room = grid.add_room(kind, Rect(x, y, w, h), ROOM_FLOOR.get(kind, "plaza"))
            room.door_side = OPPOSITE[side]
            _connect(grid, room, ring, side, conn)
            rooms.append(room)
    return rooms


def _connect(grid, room, ring, side, conn):
    """A short airlock corridor from the ring band to the room."""
    r = room.rect
    if side in ("N", "S"):
        lo = max(r.x + 1, ring.x + RING_WIDTH)
        hi = min(r.right - 1 - CORRIDOR_WIDTH, ring.right - RING_WIDTH - CORRIDOR_WIDTH)
        x = grid.rng.randint(lo, max(lo, hi))
        y = r.bottom if side == "N" else ring.bottom
        rect = Rect(x, y, CORRIDOR_WIDTH, conn)
        room.doors = [(cx, r.bottom - 1 if side == "N" else r.y) for cx in range(x, x + CORRIDOR_WIDTH)]
        _door_decor(grid, [(cx, y if side == "N" else y + conn - 1) for cx in range(x, x + CORRIDOR_WIDTH)], False)
    else:
        lo = max(r.y + 1, ring.y + RING_WIDTH)
        hi = min(r.bottom - 1 - CORRIDOR_WIDTH, ring.bottom - RING_WIDTH - CORRIDOR_WIDTH)
        y = grid.rng.randint(lo, max(lo, hi))
        x = r.right if side == "W" else ring.right
        rect = Rect(x, y, conn, CORRIDOR_WIDTH)
        room.doors = [(r.right - 1 if side == "W" else r.x, cy) for cy in range(y, y + CORRIDOR_WIDTH)]
        _door_decor(grid, [(x if side == "W" else x + conn - 1, cy) for cy in range(y, y + CORRIDOR_WIDTH)], True)
    grid.carve(rect, "corridor")


def _dress_ring(grid, ring, rooms):
    """A few maintenance bots and wall terminals along the ring's outer wall."""
    clear = set()
    for room in rooms:
        clear |= grid.room_keep_clear(room, margin=3)
    edge = ([(x, ring.y) for x in range(ring.x, ring.right)] +
            [(x, ring.bottom - 1) for x in range(ring.x, ring.right)] +
            [(ring.x, y) for y in range(ring.y, ring.bottom)] +
            [(ring.right - 1, y) for y in range(ring.y, ring.bottom)])
    for x, y in grid.rng.sample(edge, len(edge) // 10):
        grid.place(grid.rng.choice(["bot_a", "bot_b", "bot_c", "terminal_c"]), x, y, clear)


def _background(grid):
    rng = grid.rng
    cells = {}
    for cell, style in grid.floor.items():
        main, variant, chance = FLOORS.get(style, FLOORS["corridor"])
        cells[cell] = extra(variant if rng.random() < chance else main)
    outside = grid.exterior()
    for y in range(grid.height):
        for x in range(grid.width):
            cell = (x, y)
            if cell in grid.floor or cell in grid.walls:
                continue
            if cell in outside:
                if rng.random() < STAR_DENSITY:
                    cells[cell] = extra(rng.choice(STARS))
            else:
                cells[cell] = extra("hull")
    return cells


# ---- furnishing -----------------------------------------------------------------

STALL_GOODS = ["sack_gold", "sack_blue", "chest", "sack_gold", "chest"]
BEDS = ["bed_white", "bed_orange", "bed_green"]


def _stall(grid, x, y, length, clear):
    for i in range(length):
        grid.place(grid.rng.choice(STALL_GOODS), x + i, y, clear)


def _furnish_market(grid, room):
    rng = grid.rng
    r = room.rect
    clear = grid.room_keep_clear(room)
    grid.place("dome", r.cx - 2, r.cy - 1, clear)
    for side in ("N", "S"):
        for offset in rng.sample([-7, -4, 4, 7], 2):
            x, y = flush(room, side, "terminal", offset)
            if grid.add_object("Market Terminal", x, y, keep_clear=clear):
                add_posts(grid, "Dockworker", [front_of(room, side, x, y)])
    # Stall rows either side of the dome, with an aisle to walk between them.
    for sx in (r.x + 3, r.right - 6):
        for sy in (r.cy - 3, r.cy + 3):
            _stall(grid, sx, sy, 3, clear)
    along_walls(grid, room, ["locker", "control_panel", "fuel_tanks"], rng.randint(2, 4), clear, sides=("W", "E"))
    for corner in ((r.x, r.y), (r.right - 2, r.y), (r.x, r.bottom - 3), (r.right - 2, r.bottom - 3)):
        grid.place("pillars", *corner, keep_clear=clear)
    add_posts(grid, "Security", [(r.cx - 3, r.cy + 2), (r.cx + 3, r.cy - 2)])


def _furnish_docking_bay(grid, room):
    rng = grid.rng
    r = room.rect
    outer = OPPOSITE[room.door_side]
    clear = grid.room_keep_clear(room, margin=3)

    hatch_x, hatch_y = flush(room, outer, "hatch")
    grid.place("hatch", hatch_x, hatch_y, clear, check=False)

    # Landing pad: hazard ring with a docked vessel, set back from the hatch.
    pad_cx = r.cx + (-2 if outer == "W" else 2 if outer == "E" else 0)
    pad_cy = r.cy + (-1 if outer == "N" else 1 if outer == "S" else 0)
    pad = Rect(pad_cx - 2, pad_cy - 2, 5, 5)
    for cell in pad.cells():
        if not Rect(pad.x + 1, pad.y + 1, 3, 3).contains(*cell):
            grid.decor[cell] = extra("floor_hazard")
    vessel = "lander" if not any(rm.kind == "docking_bay" for rm in grid.rooms[: grid.rooms.index(room)]) else "lander_hot"
    grid.place(vessel, pad.x + 1, pad.y + 1, clear, check=False)

    first_bay = vessel == "lander"
    for side in ("N", "S") if outer in ("W", "E") else ("W", "E"):
        x, y = flush(room, side, "terminal", rng.randint(-3, 3))
        if grid.add_object("Docking Terminal", x, y, keep_clear=clear):
            add_posts(grid, "Foreman", [front_of(room, side, x, y)])
            if first_bay and grid.spawn is None:
                grid.spawn = front_of(room, side, x, y)

    along_walls(grid, room, ["fuel_tanks", "locker", "locker", "bot_a", "bot_c"], rng.randint(3, 5), clear,
                sides=tuple(s for s in ("N", "S", "E", "W") if s not in (room.door_side, outer)))

    add_posts(grid, "Dockworker", [(pad.x - 1, pad.cy), (pad.right, pad.cy), (pad.cx, pad.y - 1), (pad.cx, pad.bottom)])
    door = room.doors[len(room.doors) // 2]
    inward = {"N": (0, 2), "S": (0, -2), "W": (2, 0), "E": (-2, 0)}[room.door_side]
    side_step = (0, 2) if room.door_side in ("W", "E") else (2, 0)
    add_posts(grid, "Security", [(door[0] + inward[0] + side_step[0], door[1] + inward[1] + side_step[1])])

    if first_bay and grid.spawn is None:
        grid.spawn = (pad.right, pad.cy)


def _furnish_cantina(grid, room):
    rng = grid.rng
    r = room.rect
    clear = grid.room_keep_clear(room)
    back = "N" if room.door_side != "N" else "S"
    bar_x, bar_y = flush(room, back, "bar_front", rng.randint(-2, 2))
    if grid.place("bar_front", bar_x, bar_y, clear):
        counter = (bar_x + 1, bar_y + 1 if back == "N" else bar_y)
        grid.objects.append(("Bar Counter", *counter))
        stand = (counter[0], counter[1] + 1) if back == "N" else (counter[0], counter[1] - 1)
        add_posts(grid, "Dockworker", [(stand[0] - 1, stand[1]), (stand[0] + 1, stand[1])])
        shelf_y = r.y if back == "N" else r.bottom - 1
        for sx in (bar_x - 3, bar_x - 2, bar_x + 4, bar_x + 5):
            grid.place("shelf", sx, shelf_y, clear)
    along_walls(grid, room, ["jukebox"], 1, clear, sides=tuple(s for s in ("W", "E") if s != room.door_side))

    inner = Rect(r.x + 2, r.y + 3, r.w - 4, r.h - 5) if back == "N" else Rect(r.x + 2, r.y + 2, r.w - 4, r.h - 5)
    for _ in range(rng.randint(3, 4)):
        seat = _table_with_chairs(grid, inner, clear)
        if seat:
            add_posts(grid, "Dockworker", [seat])
    add_posts(grid, "Security", [(r.cx, r.bottom - 2 if back == "N" else r.y + 1)])


def _table_with_chairs(grid, area, clear, attempts=40):
    """A table with a chair either side, spaced so every seat stays reachable. Returns a standing cell."""
    for _ in range(attempts):
        tx, ty = grid.rng.randint(area.x + 1, area.right - 2), grid.rng.randint(area.y, area.bottom - 1)
        cells = [(tx - 1, ty), (tx, ty), (tx + 1, ty)]
        margin = [(x, y) for x in range(tx - 2, tx + 3) for y in (ty - 1, ty + 1)]
        if all(grid.walkable(c) and c not in clear for c in cells + margin):
            grid.place("chair", tx - 1, ty, clear)
            grid.place("table", tx, ty, clear)
            grid.place("chair", tx + 1, ty, clear)
            return tx, ty + 1
    return None


def _furnish_command(grid, room):
    rng = grid.rng
    clear = grid.room_keep_clear(room)
    back = OPPOSITE[room.door_side]
    horizontal_back = back in ("N", "S")
    cx, cy = flush(room, back, "console")
    if grid.place("console", cx, cy, clear):
        grid.objects.append(("Command Console", *_console_face(back, cx, cy)))
        stand = front_of(room, back, cx, cy, height=3, width=3)
        add_posts(grid, "Politician", [stand, (stand[0] - 2, stand[1]), (stand[0] + 2, stand[1])])
    if horizontal_back:
        for offset in (-5, 5):
            grid.place("cabinets", *flush(room, back, "cabinets", offset), keep_clear=clear)
    side_walls = ("W", "E") if horizontal_back else ("N", "S")
    along_walls(grid, room, ["control_panel", "terminal_b", "terminal_c", "servitor"], rng.randint(3, 4), clear,
                sides=side_walls)
    r = room.rect
    add_posts(grid, "Politician", [(r.cx - 3, r.cy + 1), (r.cx + 3, r.cy + 1)])
    door = room.doors[len(room.doors) // 2]
    add_posts(grid, "Security", [(door[0] + (2 if horizontal_back else 0), door[1] + (0 if horizontal_back else 2))])


def _console_face(back, x, y):
    """The console tile the player faces when standing in front of it."""
    return {"N": (x + 1, y + 2), "S": (x + 1, y), "W": (x + 2, y + 1), "E": (x, y + 1)}[back]


def _furnish_housing(grid, room):
    """A worker dormitory: a row of beds on the back wall, lockers on the sides, a common table."""
    rng = grid.rng
    r = room.rect
    clear = grid.room_keep_clear(room)
    back = OPPOSITE[room.door_side]

    bunks = []
    bed = rng.choice(BEDS)
    if back in ("N", "S"):
        y = r.y if back == "N" else r.bottom - 2
        for x in range(r.x + 1, r.right - 2, 3):
            if grid.place(bed, x, y, clear):
                bunks.append(front_of(room, back, x, y, height=2, width=2))
    else:
        x = r.x if back == "W" else r.right - 2
        for y in range(r.y, r.bottom - 1, 3):
            if grid.place(bed, x, y, clear):
                bunks.append(front_of(room, back, x, y, height=2, width=2))

    side_walls = ("W", "E") if back in ("N", "S") else ("N", "S")
    along_walls(grid, room, ["locker", "locker", "shelf", "chest"], rng.randint(3, 5), clear, sides=side_walls)

    common = Rect(r.x + 3, r.y + 2, r.w - 6, r.h - 4)
    seat = _table_with_chairs(grid, common, clear)

    add_posts(grid, "Miner", rng.sample(bunks, min(3, len(bunks))))
    if seat:
        add_posts(grid, "Dockworker", [seat])
        add_posts(grid, "Miner", [(seat[0], seat[1] - 2)])


def _furnish_generic(grid, room):
    along_walls(grid, room, ["locker", "control_panel", "bot_b"], 3, grid.room_keep_clear(room))


FURNISH = {
    "market": _furnish_market,
    "docking_bay": _furnish_docking_bay,
    "cantina": _furnish_cantina,
    "command": _furnish_command,
    "housing": _furnish_housing,
}
