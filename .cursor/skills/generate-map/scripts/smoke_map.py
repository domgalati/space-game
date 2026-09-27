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
from collections import deque

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

NEIGHBORS = ((1, 0), (-1, 0), (0, 1), (0, -1))


def main(path):
    import pygame
    from pytmx.util_pygame import load_pygame

    pygame.init()
    pygame.display.set_mode((1, 1))
    data = load_pygame(path)
    props = data.properties or {}
    if "mapgen_seed" not in props:
        print(f"HANDMADE: {path} has no mapgen_seed. Do not regenerate it.")
        return 2

    problems = []
    tile = data.tilewidth
    walkable = {(x, y) for x, y, gid in data.get_layer_by_name("walkable") if gid}
    if not walkable:
        problems.append("no walkable tiles")

    spawn = _named_point(data, "Spawns", "Player Start", tile)
    if spawn is None:
        problems.append("no Player Start spawn")
    elif spawn not in walkable:
        problems.append(f"Player Start {spawn} is not walkable")
    elif not _connected(spawn, walkable):
        problems.append("walkable floor is split; the spawn cannot reach every tile")

    for obj in _layer(data, "Objects"):
        point = (int(obj.x) // tile, int(obj.y) // tile)
        if not any((point[0] + dx, point[1] + dy) in walkable for dx, dy in NEIGHBORS):
            problems.append(f"{obj.name} at {point} has no walkable side")

    jobs = _jobs(props.get("npc_jobs", ""))
    posts = {}
    for obj in _layer(data, "NPC Posts"):
        point = (int(obj.x) // tile, int(obj.y) // tile)
        posts.setdefault(obj.name, []).append(point)
        if point not in walkable:
            problems.append(f"{obj.name} post at {point} is not walkable")
    for job in jobs:
        if job not in posts:
            problems.append(f"{job} is in npc_jobs but has no NPC Posts")

    if problems:
        print(f"FAIL {path}")
        for problem in problems:
            print(f"  - {problem}")
        return 1

    print(
        f"OK {data.width}x{data.height} walkable={len(walkable)} "
        f"objects={len(_layer(data, 'Objects'))} spawn={spawn} jobs={jobs}"
    )
    return 0


def _layer(data, name):
    try:
        return list(data.get_layer_by_name(name))
    except ValueError:
        return []


def _named_point(data, layer, name, tile):
    for obj in _layer(data, layer):
        if obj.name == name:
            return (int(obj.x) // tile, int(obj.y) // tile)
    return None


def _connected(start, walkable):
    seen = {start}
    queue = deque([start])
    while queue:
        x, y = queue.popleft()
        for dx, dy in NEIGHBORS:
            nxt = (x + dx, y + dy)
            if nxt in walkable and nxt not in seen:
                seen.add(nxt)
                queue.append(nxt)
    return len(seen) == len(walkable)


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
