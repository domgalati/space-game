from dialogue import topics

TERMINAL_TYPES = {
    "Docking Terminal": "docking",
    "Refinery Computer": "docking",
    "Market Terminal": "market",
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
        self.start_conversation_callback = None
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
        # One interaction per press: an adjacent object wins over an adjacent NPC.
        for pos in _cardinal_pixel_neighbors(player_position, tile_size):
            is_interactable, objectname = self.is_interactable_at(pos, tile_size)
            if is_interactable:
                self.handle_interaction_with(objectname)
                return

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
        if objectname in TERMINAL_TYPES:
            if self.activate_terminal_callback:
                self.activate_terminal_callback(TERMINAL_TYPES[objectname])
        elif objectname == "Bar Counter":
            here = self.economy.planet_name if self.economy else None
            self.logger.add_log_message("The bartender slides a drink over and leans in.")
            book = self.economy.data if self.economy else None
            self.logger.add_log_message(f'"{topics.market_rumor(here, markets=book)}"')
        elif objectname == "Command Console":
            self.logger.add_log_message("ACCESS RESTRICTED: Assembly command staff only.")

    def handle_interaction_with_npc(self, npc):
        if self.start_conversation_callback:
            self.start_conversation_callback(npc)

    def set_terminal_callback(self, callback):
        self.activate_terminal_callback = callback

    def set_conversation_callback(self, callback):
        self.start_conversation_callback = callback
