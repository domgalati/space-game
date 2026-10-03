import importlib
import random
import zlib

from entities.npcs.npc import NPC
from entities.npcs.portrait import roll_appearance
from entities.npcs.species import SPECIES, roll_species

DEFAULT_SPRITE = "space/assets/img/objects/dockworker.png"


def _guild_module(guild):
    return importlib.import_module(f".{guild}_npc", package="entities.npcs")


def roll_npc_record(npc_id, job, guild):
    """A resident rolled from their id, so the same id always makes the same person."""
    rng = random.Random(zlib.crc32(npc_id.encode("utf-8")))
    module = _guild_module(guild)
    species = roll_species(rng)
    names = SPECIES[species]
    hobbies = list(dict.fromkeys(module.hobbies))
    return {
        "id": npc_id,
        "firstname": rng.choice(names.get("first_names") or module.first_names),
        "lastname": rng.choice(names.get("last_names") or module.last_names),
        "job": job,
        "guild": guild,
        "species": species,
        "hobbies": rng.sample(hobbies, 3),
        "portrait": roll_appearance(npc_id, species, job, guild),
    }


def build_npc(record):
    """An NPC instance from a roster record or an authored character record."""
    module = _guild_module(record["guild"])
    npc_class = getattr(module, record["job"], None)
    npc = npc_class() if isinstance(npc_class, type) and issubclass(npc_class, NPC) else NPC()
    npc.npc_id = record["id"]
    npc.firstname = record["firstname"]
    npc.lastname = record["lastname"]
    npc.job_title = record["job"]
    npc.guild = record["guild"]
    npc.species = record.get("species", "human")
    npc.hobbies = list(record.get("hobbies", []))
    npc.portrait_recipe = record.get("portrait")
    npc.dialogue_file = record.get("dialogue")
    npc.start_node = record.get("start_node") or "Start"
    npc.base_mood = record.get("mood")
    npc.sprite = record.get("sprite") or npc.sprite or DEFAULT_SPRITE
    return npc
