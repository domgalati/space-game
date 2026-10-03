"""Approved world sprites. Dialogue portraits have their own manifest."""

_ROOT = "space/assets/img/npcs"
_ASSEMBLY_JOBS = ("Miner", "Foreman", "Dockworker", "Security", "Politician")

MAP_SPRITES = {
    "assembly": {
        job: {
            species: f"{_ROOT}/assembly/{species}/{job.lower()}.png"
            for species in ("human", "vessari", "muroth")
        }
        for job in _ASSEMBLY_JOBS
    }
}


def map_sprite(guild, job, species):
    """Resolve a known role; unfamiliar species use its human art.

    Unknown guilds/jobs return None so the caller can retain class/default art.
    """
    variants = MAP_SPRITES.get(guild, {}).get(job, {})
    return variants.get(species) or variants.get("human")
