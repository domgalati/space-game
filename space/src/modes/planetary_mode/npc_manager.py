import pygame
import random

from util.config import TILE_SIZE, resolve_game_path
from entities.npcs.goals.hang_near_goal import HangNearGoal
from entities.npcs.goals.wander_goal import WanderGoal
from entities.npcs.npc_generator import build_npc
from world.characters import POST_PREFIX, character_record, load_character


# Keep populations small enough that job goals are visible on Terramonta.
_TOTAL_NPC_CAP = 12

_JOB_TARGETS = {
    "Miner": "mining_machines",
    "Foreman": "terminals",
}

_TARGET_ACTIVITIES = {
    "mining_machines": "keeping the rigs running",
    "terminals": "keeping an eye on the terminals",
}


class NPCManager:
    def __init__(self, map_manager, planet, roster):
        self.map_manager = map_manager
        self.planet = planet
        self.roster = roster
        self.npcs = []
        self._walkable_tiles_cache = None
        self._sprite_cache = {}
        self.map_properties = map_manager.tmx_data.properties
        self.mining_machine_tiles = self._collect_layer_tiles("Mining Machines")
        self.terminal_tiles = self._collect_object_tiles(
            ("Docking Terminal", "Refinery Computer")
        )
        self.post_tiles, self.character_posts = self._collect_posts()
        self.populate_npcs()

    def populate_npcs(self):
        walkable_tiles = self.get_walkable_tiles()
        if not walkable_tiles:
            return

        guild_name = self.map_properties.get("guild") or self.planet.planet_guild
        records = self.roster.for_location(self.planet.id, self.get_npc_counts(), guild_name)
        for record in records:
            npc = build_npc(record)
            posts = self.post_tiles.get(npc.job_title)
            if posts:
                # Each NPC keeps a couple of posts so a crew spreads out instead of stacking.
                posts = random.sample(posts, min(2, len(posts)))
                npc.goal = HangNearGoal(npc, posts, activity="on shift")
                npc.position = self._tile_near(posts[0], walkable_tiles)
            else:
                npc.position = random.choice(walkable_tiles)
                self._assign_goal(npc)
            self._add(npc)

        for char_id, tiles in self.character_posts.items():
            try:
                definition = load_character(char_id)
            except (OSError, ValueError) as exc:
                print(f"Skipping character post {char_id!r}: {exc}")
                continue
            npc = build_npc(character_record(definition))
            post = tiles[0]
            npc.position = post if post in walkable_tiles else self._tile_near(post, walkable_tiles)
            npc.goal = HangNearGoal(npc, [post], activity=definition.get("activity"))
            self._add(npc)

    def _add(self, npc):
        npc.npc_manager = self
        if npc.sprite:
            npc.sprite_image = self._load_sprite(npc.sprite)
        self.npcs.append(npc)

    def _load_sprite(self, path):
        if path not in self._sprite_cache:
            self._sprite_cache[path] = pygame.image.load(resolve_game_path(path)).convert_alpha()
        return self._sprite_cache[path]

    def get_npc_counts(self):
        """Job -> headcount; maps can set an npc_jobs property like "Security:3,Dockworker:5"."""
        spec = self.map_properties.get("npc_jobs")
        if spec:
            counts = {}
            for entry in spec.split(","):
                job, _, count = entry.partition(":")
                counts[job.strip()] = int(count or 1)
            return counts
        npc_types = self.get_npc_types_based_on_planet(self.planet)
        per_type = max(1, _TOTAL_NPC_CAP // max(1, len(npc_types)))
        return {npc_type: per_type for npc_type in npc_types}

    def _tile_near(self, target, walkable_tiles, radius=3):
        tx, ty = target
        nearby = [t for t in walkable_tiles if abs(t[0] - tx) <= radius and abs(t[1] - ty) <= radius]
        return random.choice(nearby or walkable_tiles)

    def _collect_posts(self):
        """Job posts ({job: [tile]}) and authored-character posts ({character id: [tile]})."""
        posts = {}
        characters = {}
        try:
            layer = self.map_manager.tmx_data.get_layer_by_name("NPC Posts")
        except ValueError:
            return posts, characters
        for obj in layer:
            tile = (int(obj.x) // TILE_SIZE, int(obj.y) // TILE_SIZE)
            name = obj.name or ""
            if name.startswith(POST_PREFIX):
                characters.setdefault(name[len(POST_PREFIX):], []).append(tile)
            else:
                posts.setdefault(name, []).append(tile)
        return posts, characters

    def _assign_goal(self, npc):
        target_key = _JOB_TARGETS.get(npc.job_title)
        activity = _TARGET_ACTIVITIES.get(target_key)
        if target_key == "mining_machines" and self.mining_machine_tiles:
            npc.goal = HangNearGoal(npc, self.mining_machine_tiles, activity=activity)
        elif target_key == "terminals" and self.terminal_tiles:
            npc.goal = HangNearGoal(npc, self.terminal_tiles, activity=activity)
        else:
            npc.goal = WanderGoal(npc)

    def _collect_layer_tiles(self, layer_name):
        tiles = []
        try:
            layer = self.map_manager.tmx_data.get_layer_by_name(layer_name)
        except ValueError:
            return tiles
        for x, y, gid in layer:
            if gid != 0:
                tiles.append((x, y))
        return tiles

    def _collect_object_tiles(self, names):
        tiles = []
        seen = set()
        try:
            objects_layer = self.map_manager.tmx_data.get_layer_by_name("Objects")
        except ValueError:
            return tiles
        for obj in objects_layer:
            if obj.name not in names:
                continue
            tile = (int(obj.x) // TILE_SIZE, int(obj.y) // TILE_SIZE)
            if tile not in seen:
                seen.add(tile)
                tiles.append(tile)
        return tiles

    def get_npc_types_based_on_planet(self, planet):
        if getattr(planet, "planet_type", None) == "Industrial":
            return ["Miner", "Foreman"]
        return ["Miner"]

    def get_walkable_tiles(self):
        if self._walkable_tiles_cache is not None:
            return self._walkable_tiles_cache
        walkable_tiles = []
        walkable_layer = self.map_manager.tmx_data.get_layer_by_name("walkable")
        for x, y, gid in walkable_layer:
            if gid != 0:
                walkable_tiles.append((x, y))
        self._walkable_tiles_cache = walkable_tiles
        return walkable_tiles

    def is_within_visible_area(self, npc_x, npc_y, camera_x, camera_y, camera_width, camera_height):
        npc_pixel_x = npc_x * TILE_SIZE
        npc_pixel_y = npc_y * TILE_SIZE
        return (
            camera_x <= npc_pixel_x <= camera_x + camera_width
            and camera_y <= npc_pixel_y <= camera_y + camera_height
        )

    def update(self, camera_x, camera_y, camera_width, camera_height, player_tile=None):
        for npc in self.npcs:
            if player_tile is not None and self._is_adjacent_to_player(npc.position, player_tile):
                continue  # stay put so the player can press E
            if self.is_within_visible_area(
                npc.position[0], npc.position[1], camera_x, camera_y, camera_width, camera_height
            ):
                npc.update()

    def _is_adjacent_to_player(self, npc_tile, player_tile):
        dx = abs(npc_tile[0] - player_tile[0])
        dy = abs(npc_tile[1] - player_tile[1])
        return max(dx, dy) == 1

    def draw(self, npc_layer, camera):
        npc_layer.fill((0, 0, 0, 0))
        for npc in self.npcs:
            if self.is_within_visible_area(
                npc.position[0], npc.position[1], camera.x, camera.y, camera.width, camera.height
            ):
                if npc.sprite:
                    sprite_image = npc.sprite_image
                    npc_screen_x = npc.position[0] * TILE_SIZE - camera.x
                    npc_screen_y = npc.position[1] * TILE_SIZE - camera.y
                    npc_layer.blit(sprite_image, (npc_screen_x, npc_screen_y))
