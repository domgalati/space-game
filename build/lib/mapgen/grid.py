"""Theme-agnostic map model: floor regions, walls, props, interactables and NPC posts."""
from collections import deque

from . import extras
from .tiles import STAMPS, extra

NEIGHBORS_4 = ((0, -1, extras.N), (1, 0, extras.E), (0, 1, extras.S), (-1, 0, extras.W))


class Rect:
    def __init__(self, x, y, w, h):
        self.x, self.y, self.w, self.h = x, y, w, h

    @property
    def right(self):
        return self.x + self.w

    @property
    def bottom(self):
        return self.y + self.h

    @property
    def cx(self):
        return self.x + self.w // 2

    @property
    def cy(self):
        return self.y + self.h // 2

    def cells(self):
        for y in range(self.y, self.bottom):
            for x in range(self.x, self.right):
                yield x, y

    def inflate(self, d):
        return Rect(self.x - d, self.y - d, self.w + 2 * d, self.h + 2 * d)

    def contains(self, x, y):
        return self.x <= x < self.right and self.y <= y < self.bottom

    def overlaps(self, other):
        return self.x < other.right and other.x < self.right and self.y < other.bottom and other.y < self.bottom


class Room:
    def __init__(self, kind, rect, floor):
        self.kind = kind
        self.rect = rect
        self.floor = floor
        self.doors = []  # (x, y) floor cells just inside each opening


class Grid:
    def __init__(self, width, height, rng):
        self.width = width
        self.height = height
        self.rng = rng
        self.floor = {}  # (x, y) -> floor style
        self.walls = set()
        self.decor = {}  # (x, y) -> gid drawn over floor, still walkable
        self.props = {}  # (x, y) -> gid, solid
        self.rooms = []
        self.objects = []  # (name, x, y) interactables
        self.posts = []  # (job, x, y)
        self.spawn = None
        self.background = {}  # (x, y) -> gid for non-floor cells (stars, hull fill)

    # ---- carving -------------------------------------------------------------
    def in_bounds(self, x, y):
        return 0 <= x < self.width and 0 <= y < self.height

    def carve(self, rect, floor):
        for x, y in rect.cells():
            if self.in_bounds(x, y):
                self.floor[(x, y)] = floor

    def add_room(self, kind, rect, floor):
        room = Room(kind, rect, floor)
        self.carve(rect, floor)
        self.rooms.append(room)
        return room

    def add_wall_ring(self, rect, gaps=()):
        """Explicit walls around rect (for compounds on open ground); gaps stay floor."""
        outline = rect.inflate(1)
        for x, y in outline.cells():
            if outline.contains(x, y) and not rect.contains(x, y) and (x, y) not in gaps:
                self.walls.add((x, y))
                self.floor.pop((x, y), None)

    def derive_walls(self):
        """Every non-floor cell touching floor (8-way) becomes wall: rooms seal themselves."""
        for (x, y) in list(self.floor):
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    cell = (x + dx, y + dy)
                    if cell not in self.floor and self.in_bounds(*cell):
                        self.walls.add(cell)

    # ---- queries -------------------------------------------------------------
    def walkable(self, cell):
        return cell in self.floor and cell not in self.props

    def walkable_cells(self):
        return [cell for cell in self.floor if cell not in self.props]

    def connected(self, extra_blocked=()):
        cells = [c for c in self.walkable_cells() if c not in extra_blocked]
        if not cells:
            return True
        blocked = set(extra_blocked)
        seen = {cells[0]}
        queue = deque([cells[0]])
        while queue:
            x, y = queue.popleft()
            for dx, dy, _ in NEIGHBORS_4:
                nxt = (x + dx, y + dy)
                if nxt not in seen and self.walkable(nxt) and nxt not in blocked:
                    seen.add(nxt)
                    queue.append(nxt)
        return len(seen) == len(cells)

    # ---- props ---------------------------------------------------------------
    def stamp_fits(self, stamp, x, y, keep_clear=()):
        for dy in range(stamp.height):
            for dx in range(stamp.width):
                cell = (x + dx, y + dy)
                if not self.walkable(cell) or cell in keep_clear or cell in self.decor:
                    return False
        return True

    def place(self, name, x, y, keep_clear=(), check=True):
        """Place a solid stamp if it fits and leaves every floor cell reachable."""
        stamp = STAMPS[name]
        if not self.stamp_fits(stamp, x, y, keep_clear):
            return False
        footprint = [(x + dx, y + dy) for dy in range(stamp.height) for dx in range(stamp.width)]
        if check and not self.connected(extra_blocked=footprint):
            return False
        for dy, row in enumerate(stamp.tiles):
            for dx, gid in enumerate(row):
                self.props[(x + dx, y + dy)] = gid
        return True

    def scatter(self, name, area, count, keep_clear=(), attempts=40):
        placed = []
        stamp = STAMPS[name]
        for _ in range(count):
            for _ in range(attempts):
                x = self.rng.randint(area.x, area.right - stamp.width)
                y = self.rng.randint(area.y, area.bottom - stamp.height)
                if self.place(name, x, y, keep_clear):
                    placed.append((x, y))
                    break
        return placed

    def add_object(self, name, x, y, stamp="terminal", keep_clear=()):
        """An interactable tile (terminal, counter...) the player uses by standing beside it."""
        if stamp and not self.place(stamp, x, y, keep_clear):
            return False
        self.objects.append((name, x, y))
        return True

    def room_keep_clear(self, room, margin=2):
        """Cells in front of a room's doors that props must not block."""
        clear = set()
        for dx0, dy0 in room.doors:
            for dx in range(-margin, margin + 1):
                for dy in range(-margin, margin + 1):
                    clear.add((dx0 + dx, dy0 + dy))
        return clear

    # ---- tile layers ---------------------------------------------------------
    def wall_gids(self):
        gids = {}
        for (x, y) in self.walls:
            mask = 0
            for dx, dy, bit in NEIGHBORS_4:
                if (x + dx, y + dy) in self.walls:
                    mask |= bit
            horizontal = mask & (extras.E | extras.W)
            vertical = mask & (extras.N | extras.S)
            # Stacked walls (two rooms two cells apart) read better as parallel runs.
            if horizontal == (extras.E | extras.W) and vertical:
                mask = horizontal
            elif vertical == (extras.N | extras.S) and horizontal:
                mask = vertical
            gids[(x, y)] = extra(f"wall_{mask}")
        return gids

    def exterior(self):
        """Non-floor, non-wall cells reachable from the map border (open space / open ground)."""
        seen = set()
        queue = deque()
        for x in range(self.width):
            for y in (0, self.height - 1):
                queue.append((x, y))
        for y in range(self.height):
            for x in (0, self.width - 1):
                queue.append((x, y))
        while queue:
            cell = queue.popleft()
            if cell in seen or not self.in_bounds(*cell) or cell in self.walls or cell in self.floor:
                continue
            seen.add(cell)
            x, y = cell
            for dx, dy, _ in NEIGHBORS_4:
                queue.append((x + dx, y + dy))
        return seen
