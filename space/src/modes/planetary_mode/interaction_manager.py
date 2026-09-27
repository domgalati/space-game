import random

from util.config import TILE_SIZE


# Job -> goods this person notices on talk (must exist in planet economy YAML).
JOB_GOODS_BIAS = {
    "Miner": ("Raw Minerals", "Steel"),
    "Foreman": ("Mining Equipment", "Durable Tools"),
}


def _cardinal_pixel_neighbors(player_position, tile_size):
    x, y = player_position[0], player_position[1]
    return [
        (x, y - tile_size),
        (x, y + tile_size),
        (x - tile_size, y),
        (x + tile_size, y),
    ]


def _chebyshev_adjacent_tiles(player_tile):
    """All 8 neighboring tiles around the player (plus not the player tile itself)."""
    px, py = player_tile
    return [
        (px + dx, py + dy)
        for dx in (-1, 0, 1)
        for dy in (-1, 0, 1)
        if not (dx == 0 and dy == 0)
    ]


class InteractionManager:
    def __init__(self, map_manager, npc_manager, logger, economy=None):
        self.map_manager = map_manager
        self.logger = logger
        self.interacted = False
        self.activate_terminal_callback = None
        self.npc_manager = npc_manager
        self.economy = economy
        self._announced_npc_ids = set()
        self._announced_object_names = set()

    def is_interactable_at(self, position, tile_size):
        """
        Check if the tile at the given position is in the Objects layer.
        """
        y, x = position
        tile_x, tile_y = x // tile_size, y // tile_size
        if 0 <= tile_x and 0 <= tile_y:
            objects_layer = self.map_manager.tmx_data.get_layer_by_name("Objects")
            for i in range(len(objects_layer)):
                if objects_layer[i].x == y and objects_layer[i].y == x:
                    objectname = objects_layer[i].name
                    return True, objectname
        return False, None

    def adjacent_npcs(self, player_position, tile_size):
        player_tile = (player_position[0] // tile_size, player_position[1] // tile_size)
        neighbor_tiles = set(_chebyshev_adjacent_tiles(player_tile))
        return [npc for npc in self.npc_manager.npcs if npc.position in neighbor_tiles]

    def check_for_adjacent_interactables(self, player_position, tile_size):
        # Terminals / objects: cardinal only (matches bump geometry on the map).
        adjacent_object_names = set()
        for pos in _cardinal_pixel_neighbors(player_position, tile_size):
            is_interactable, objectname = self.is_interactable_at(pos, tile_size)
            if is_interactable:
                adjacent_object_names.add(objectname)

        self._announced_object_names &= adjacent_object_names
        for objectname in adjacent_object_names:
            if objectname not in self._announced_object_names:
                self.logger.add_log_message(
                    f"You approach a {objectname}. Press E to interact."
                )
                self._announced_object_names.add(objectname)
                break

        # Drop announcements for NPCs no longer nearby.
        nearby = self.adjacent_npcs(player_position, tile_size)
        nearby_ids = {id(npc) for npc in nearby}
        self._announced_npc_ids &= nearby_ids

        newly_seen = False
        for npc in nearby:
            npc_id = id(npc)
            if npc_id in self._announced_npc_ids:
                continue
            job = npc.job_title or "worker"
            self.logger.add_log_message(
                f"You see {npc.firstname} {npc.lastname} ({job}). Press E to interact."
            )
            self._announced_npc_ids.add(npc_id)
            newly_seen = True
            break  # one new introduction per player turn

        return newly_seen or bool(nearby)

    def interact(self, player_position, tile_size):
        for pos in _cardinal_pixel_neighbors(player_position, tile_size):
            is_interactable, objectname = self.is_interactable_at(pos, tile_size)
            if is_interactable:
                self.handle_interaction_with(objectname)

        nearby = self.adjacent_npcs(player_position, tile_size)
        if nearby:
            # Prefer the closest NPC (Manhattan), stable for diagonals.
            px = player_position[0] // tile_size
            py = player_position[1] // tile_size
            nearby.sort(
                key=lambda n: abs(n.position[0] - px) + abs(n.position[1] - py)
            )
            self.handle_interaction_with_npc(nearby[0])

    def handle_interaction_with(self, objectname):
        if objectname == "Docking Terminal" or objectname == "Refinery Computer":
            if self.activate_terminal_callback:
                self.activate_terminal_callback()

    def handle_interaction_with_npc(self, npc):
        job = npc.job_title or "worker"
        self.logger.add_log_message(
            f"Talking to {npc.firstname} {npc.lastname}, {job}."
        )
        if npc.hobbies:
            hobby = random.choice(npc.hobbies)
            self.logger.add_log_message(f"They mention enjoying {hobby}.")
        opinion = self._goods_opinion_line(npc)
        if opinion:
            self.logger.add_log_message(opinion)

    def _goods_opinion_line(self, npc):
        if not self.economy:
            return None
        goods = JOB_GOODS_BIAS.get(npc.job_title)
        if not goods:
            return None
        planet = self.economy.planet_name
        planet_data = self.economy.data.get(planet, {})
        catalog = planet_data.get("goods", {})
        available = [g for g in goods if g in catalog]
        if not available:
            return None
        item = random.choice(available)
        entry = catalog[item]
        base = entry.get("basePrice")
        current = entry.get("currentPrice", base)
        if base is None or current is None or base == 0:
            return None
        ratio = current / base
        if ratio >= 1.15:
            return f"They mutter that {item} is high lately."
        if ratio <= 0.85:
            return f"They mutter that {item} is cheap lately."
        return f"They reckon {item} is about average right now."

    def set_terminal_callback(self, callback):
        self.activate_terminal_callback = callback
