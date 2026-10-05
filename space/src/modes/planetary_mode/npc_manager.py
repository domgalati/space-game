import pygame
import random
from functools import partial

from util.config import TILE_SIZE, resolve_game_path
from util.turns import Ticker
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
    """The people on a map: who lives here, where they start, and their turns on the clock."""

    def __init__(self, ground, planet, roster, clock, player=None):
        self.ground = ground
        self.planet = planet
        self.roster = roster
        self.clock = clock  # util.turns.TurnClock; every NPC takes its turns on it
        self.player = player  # NPCs beside the player hold still, so E stays aimed at them
        self.npcs = []
        self._sprite_cache = {}
        self._turns = {}  # npc -> its Ticker on the clock
        self.map_properties = ground.properties
        self.mining_machine_tiles = ground.layer_tiles("Mining Machines")
        self.terminal_tiles = ground.object_tiles(("Docking Terminal", "Refinery Computer"))
        self.post_tiles, self.character_posts = self._collect_posts()
        self.populate_npcs()

    def populate_npcs(self):
        walkable_tiles = self.ground.walkable_tiles()
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
                self.add(npc, self._tile_near(posts[0]))
            else:
                self._assign_goal(npc)
                self.add(npc, self._free_tile())

        for char_id, tiles in self.character_posts.items():
            try:
                definition = load_character(char_id)
            except (OSError, ValueError) as exc:
                print(f"Skipping character post {char_id!r}: {exc}")
                continue
            npc = build_npc(character_record(definition))
            post = tiles[0]
            npc.goal = HangNearGoal(npc, [post], activity=definition.get("activity"))
            self.add(npc, post if self.ground.free(post) else self._tile_near(post))

    def add(self, npc, tile):
        """Bring `npc` onto the map at free `tile` and start its turns, at its speed."""
        if tile is None:
            print(f"No room on the map for {npc.npc_id}")
            return
        self.ground.place(npc, tile)
        self._turns[npc] = Ticker(partial(self.take_turn, npc), npc.speed)
        self.clock.add(self._turns[npc])
        if npc.sprite:
            npc.sprite_image = self._load_sprite(npc.sprite)
        self.npcs.append(npc)

    def remove(self, npc):
        """Take `npc` off the map and the clock: gone, or (later) fallen in a fight."""
        self.ground.remove(npc)
        self.clock.remove(self._turns.pop(npc))
        self.npcs.remove(npc)

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

    def _free_tile(self):
        """Somewhere free anywhere on the map, or None if every tile is taken."""
        free = [t for t in self.ground.walkable_tiles() if self.ground.free(t)]
        return random.choice(free) if free else None

    def _tile_near(self, target, radius=3):
        """A free tile within `radius` of `target`, else anywhere free."""
        tx, ty = target
        nearby = [t for t in self.ground.walkable_tiles()
                  if abs(t[0] - tx) <= radius and abs(t[1] - ty) <= radius and self.ground.free(t)]
        return random.choice(nearby) if nearby else self._free_tile()

    def _collect_posts(self):
        """Job posts ({job: [tile]}) and authored-character posts ({character id: [tile]})."""
        posts = {}
        characters = {}
        for name, tiles in self.ground.markers("NPC Posts").items():
            if name.startswith(POST_PREFIX):
                characters[name[len(POST_PREFIX):]] = tiles
            else:
                posts[name] = tiles
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

    def get_npc_types_based_on_planet(self, planet):
        if getattr(planet, "planet_type", None) == "Industrial":
            return ["Miner", "Foreman"]
        return ["Miner"]

    def is_within_visible_area(self, npc_x, npc_y, camera_x, camera_y, camera_width, camera_height):
        npc_pixel_x = npc_x * TILE_SIZE
        npc_pixel_y = npc_y * TILE_SIZE
        return (
            camera_x <= npc_pixel_x <= camera_x + camera_width
            and camera_y <= npc_pixel_y <= camera_y + camera_height
        )

    def take_turn(self, npc):
        """One of `npc`'s turns, on or off screen: follow its goal, unless the player is beside it."""
        if self.beside_player(npc):
            return  # stay put so the player can press E
        npc.update(self.ground)

    def beside_player(self, npc):
        here = getattr(self.player, "position", None)
        if here is None or npc.position is None:
            return False
        return max(abs(npc.position[0] - here[0]), abs(npc.position[1] - here[1])) == 1

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
