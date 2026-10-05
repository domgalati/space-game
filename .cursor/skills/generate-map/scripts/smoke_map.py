"""Headless checks for a generated map.

Exit 0: the map loads, the spawn is walkable, the floor is connected, and
every interactable has a walkable side.
Exit 1: a generated map failed a check.
Exit 2: no mapgen_seed property, so the file is hand-made. Do not regenerate it.

Usage (venv, repository root):
  python .cursor/skills/generate-map/scripts/smoke_map.py "space/assets/maps/Nexum Astra.tmx"
"""
import os
import sys
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
# Check maps the way the game reads them: through its GroundMap.
sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "space" / "src"))


def main(path):
    import pygame
    from modes.planetary_mode.ground_map import GroundMap

    pygame.init()
    pygame.display.set_mode((1, 1))
    ground = GroundMap.load(path)
    props = ground.properties
    if "mapgen_seed" not in props:
        print(f"HANDMADE: {path} has no mapgen_seed. Do not regenerate it.")
        return 2

    problems = []
    walkable = ground.walkable_tiles()
    if not walkable:
        problems.append("no walkable tiles")

    spawn = ground.spawn()
    if spawn is None:
        problems.append("no Player Start spawn")
    elif not ground.walkable(spawn):
        problems.append(f"Player Start {spawn} is not walkable")
    elif len(ground.reachable_from(spawn)) != len(walkable):
        problems.append("walkable floor is split; the spawn cannot reach every tile")

    for obj in ground.objects:
        if not any(ground.walkable(side) for side in ground.neighbours(obj.tile)):
            problems.append(f"{obj.name} at {obj.tile} has no walkable side")

    jobs = _jobs(props.get("npc_jobs", ""))
    posts = ground.markers("NPC Posts")
    for name, tiles in posts.items():
        for point in tiles:
            if not ground.walkable(point):
                problems.append(f"{name} post at {point} is not walkable")
    for job in jobs:
        if job not in posts:
            problems.append(f"{job} is in npc_jobs but has no NPC Posts")

    if problems:
        print(f"FAIL {path}")
        for problem in problems:
            print(f"  - {problem}")
        return 1

    print(
        f"OK {ground.width}x{ground.height} walkable={len(walkable)} "
        f"objects={len(ground.objects)} spawn={spawn} jobs={jobs}"
    )
    return 0


def _jobs(raw):
    jobs = {}
    for entry in raw.split(","):
        if not entry.strip():
            continue
        job, _, count = entry.partition(":")
        jobs[job.strip()] = int(count or 1)
    return jobs


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("usage: smoke_map.py <map.tmx>", file=sys.stderr)
        sys.exit(1)
    sys.exit(main(sys.argv[1]))
