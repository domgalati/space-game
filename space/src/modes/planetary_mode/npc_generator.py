import random
import importlib

def generate_npc(guild, npc_class_name):
    # Dynamically import the correct module based on the guild
    npc_module = importlib.import_module(f".{guild}_npc", package="entities.npcs")

    # Get the NPC class from the module
    npc_class = getattr(npc_module, npc_class_name)

    # Create an instance of the NPC class
    npc = npc_class()

    # Randomly select first name, last name, and hobbies
    npc.firstname = random.choice(npc_module.first_names)
    npc.lastname = random.choice(npc_module.last_names)
    npc.hobbies = random.sample(npc_module.hobbies, 3)

    # Return the initialized NPC object
    return npc

# Example usage
#npc = generate_npc("assembly", "Foreman")
#print(f"Generated NPC: {npc.firstname} {npc.lastname}, Hobbies: {', '.join(npc.hobbies)}")

