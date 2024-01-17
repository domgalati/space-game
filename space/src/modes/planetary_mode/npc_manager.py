import random
from .npc_generator import generate_npc  # Import the npc_generator function

class NPCManager:
    def __init__(self, map_manager, planet):
        self.map_manager = map_manager
        self.planet = planet
        self.npcs = []
        self.populate_npcs()

    def populate_npcs(self):
        npc_types = self.get_npc_types_based_on_planet(self.planet)
        walkable_tiles = self.get_walkable_tiles()
        guild_name = self.planet.guild  # Assuming guild name is stored in planet object

        for npc_class in npc_types:
            position = random.choice(walkable_tiles)
            # Use npc_generator to create NPC instance
            npc = generate_npc(guild_name, npc_class.__name__)
            npc.set_position(position)
            self.npcs.append(npc)

    def get_npc_types_based_on_planet(self, planet):
        # Example logic based on planet type
        if planet.type == 'Industrial':
            return [Miner, Foreman]  # More miners and foremen for a mining planet
        # Add other conditions for different planet types
        return [NPC]  # Default NPC type

    def get_walkable_tiles(self):
        walkable_tiles = []
        walkable_layer = self.map_manager.tmx_data.get_layer_by_name('walkable')
        for x, y, gid in walkable_layer:
            if gid != 0:  # Assuming non-zero GID indicates a walkable tile
                walkable_tiles.append((x, y))
        return walkable_tiles

    def update(self):
        # Update logic for NPCs, e.g., movements, interactions
        pass

    def draw(self, surface):
        # Draw NPCs on the map
        for npc in self.npcs:
            npc.draw(surface)
