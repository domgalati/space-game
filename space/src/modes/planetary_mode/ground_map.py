"""A map ashore as the game sees it: which tiles can be walked, what's on them, who stands
where, and where things are marked.

Everything that asks about the ground (walking, NPC goals, interaction, and later line of
sight and pathfinding in a ground fight) asks this, in tiles. Drawing the map is
MapRenderer's job. Positions are (x, y) tiles; whoever stands on the map (the player, NPCs)
keeps theirs in `.position`, and GroundMap keeps that and its own index in step.
"""
from collections import deque, namedtuple

from pytmx.util_pygame import load_pygame

NEIGHBOURS = ((0, -1), (0, 1), (-1, 0), (1, 0))  # the four sides you can step or reach across
AROUND = tuple((dx, dy) for dy in (-1, 0, 1) for dx in (-1, 0, 1) if dx or dy)  # all eight
WALKABLE_LAYER = "walkable"
OBJECTS_LAYER = "Objects"

MapObject = namedtuple("MapObject", "name tile properties")


class GroundMap:
    def __init__(self, tmx):
        self.tmx = tmx  # the loaded Tiled map, for MapRenderer
        self.width, self.height = tmx.width, tmx.height
        self.tile_width, self.tile_height = tmx.tilewidth, tmx.tileheight
        self.properties = dict(tmx.properties or {})  # e.g. guild, npc_jobs
        self._walkable = self.layer_tiles(WALKABLE_LAYER)
        self._walkable_set = frozenset(self._walkable)
        self.objects = [MapObject(obj.name, self.tile_at(obj.x, obj.y), dict(obj.properties or {}))
                        for obj in self._object_layer(OBJECTS_LAYER)]
        self._object_at = {}
        for obj in self.objects:
            self._object_at.setdefault(obj.tile, obj)  # the first one listed wins a shared tile
        self._occupants = {}  # tile -> who stands there

    @classmethod
    def load(cls, path):
        return cls(load_pygame(path))

    def tile_at(self, x, y):
        """The tile under map pixel (x, y)."""
        return int(x) // self.tile_width, int(y) // self.tile_height

    # The floor

    def in_bounds(self, tile):
        return 0 <= tile[0] < self.width and 0 <= tile[1] < self.height

    def walkable(self, tile):
        return tile in self._walkable_set

    def walkable_tiles(self):
        """Every walkable tile, in map order."""
        return self._walkable

    def neighbours(self, tile, sides=NEIGHBOURS):
        x, y = tile
        return [(x + dx, y + dy) for dx, dy in sides]

    def reachable_from(self, start):
        """Every walkable tile you can walk to from `start`, through the four sides."""
        if not self.walkable(start):
            return set()
        seen, queue = {start}, deque([start])
        while queue:
            for step in self.neighbours(queue.popleft()):
                if self.walkable(step) and step not in seen:
                    seen.add(step)
                    queue.append(step)
        return seen

    # What the map marks

    def object_at(self, tile):
        """The map object (a terminal, a bar counter) on `tile`, or None."""
        return self._object_at.get(tile)

    def object_tiles(self, names):
        """Tiles holding objects with any of `names`, each once, in map order."""
        return list(dict.fromkeys(obj.tile for obj in self.objects if obj.name in names))

    def layer_tiles(self, name):
        """Tiles with something drawn on them in tile layer `name`; [] if the map has no such layer."""
        try:
            layer = self.tmx.get_layer_by_name(name)
        except ValueError:
            return []
        return [(x, y) for x, y, gid in layer if gid]

    def markers(self, layer):
        """{name: [tile]} for the points in object layer `layer` (e.g. "NPC Posts", "Spawns")."""
        marks = {}
        for obj in self._object_layer(layer):
            marks.setdefault(obj.name or "", []).append(self.tile_at(obj.x, obj.y))
        return marks

    def spawn(self, name="Player Start"):
        """Where a marker in the "Spawns" layer puts you, or None if the map has none."""
        tiles = self.markers("Spawns").get(name)
        return tiles[0] if tiles else None

    def _object_layer(self, name):
        try:
            return list(self.tmx.get_layer_by_name(name))
        except ValueError:
            return []

    # Who stands where

    def occupant(self, tile):
        return self._occupants.get(tile)

    def free(self, tile):
        """Walkable, and nobody is standing there."""
        return self.walkable(tile) and tile not in self._occupants

    def place(self, who, tile):
        """Put `who` on `tile`, which must be free. Moving someone already here is move()."""
        if not self.free(tile):
            raise ValueError(f"{tile} is not free")
        self._occupants[tile] = who
        who.position = tile

    def move(self, who, tile):
        """Step `who` to free `tile`. Returns whether it could."""
        if not self.free(tile):
            return False
        self._occupants.pop(who.position, None)
        self._occupants[tile] = who
        who.position = tile
        return True

    def swap(self, first, second):
        """Trade places, as when the player squeezes past someone in a corridor."""
        a, b = first.position, second.position
        self._occupants[a], self._occupants[b] = second, first
        first.position, second.position = b, a

    def remove(self, who):
        if self._occupants.get(who.position) is who:
            del self._occupants[who.position]
        who.position = None
