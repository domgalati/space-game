"""python -m mapgen <spec.yaml> [--seed N] [--out map.tmx] [--preview map.png]"""
import argparse
import os
import random

import yaml

from util.config import resolve_game_path

from . import extras, tiles, tmx
from .themes import THEMES

MAPS_DIR = "space/assets/maps"
EXTRAS_PNG = "space/assets/img/tilesets/mapgen_extras.png"
EXTRAS_TSX = "space/assets/Tilesheet Files/mapgen_extras.tsx"


def load_spec(path):
    with open(path, "r", encoding="utf-8") as file:
        spec = yaml.safe_load(file)
    spec.setdefault("theme", "station")
    spec.setdefault("size", [100, 70])
    spec.setdefault("seed", 0)
    spec.setdefault("guild", "assembly")
    spec.setdefault("rooms", [])
    spec.setdefault("npcs", {})
    return spec


def generate(spec, seed=None, out=None):
    seed = spec["seed"] if seed is None else seed
    theme = THEMES[spec["theme"]]
    grid, background = theme.generate(spec, random.Random(seed))
    if grid.spawn is None:
        grid.spawn = min(grid.walkable_cells(), key=lambda c: (c[1], c[0]))

    out = out or resolve_game_path(f"{MAPS_DIR}/{spec['name']}.tmx")
    properties = {
        "guild": spec["guild"],
        "npc_jobs": ",".join(f"{job}:{count}" for job, count in spec["npcs"].items()),
        "mapgen_theme": spec["theme"],
        "mapgen_seed": seed,
    }
    tmx.write(grid, background, out, properties)
    return out, grid


def write_extras():
    import pygame

    extras.write_tileset(
        resolve_game_path(EXTRAS_PNG),
        resolve_game_path(EXTRAS_TSX),
        os.path.relpath(resolve_game_path(EXTRAS_PNG), os.path.dirname(resolve_game_path(EXTRAS_TSX))).replace("\\", "/"),
        tiles.prop_blocks(),
        lambda path: pygame.image.load(resolve_game_path(path)).convert_alpha(),
    )


def render_preview(tmx_path, png_path, scale=0.5):
    import pygame
    import pytmx
    from pytmx.util_pygame import load_pygame

    data = load_pygame(tmx_path)
    full = pygame.Surface((data.width * data.tilewidth, data.height * data.tileheight))
    full.fill((0, 0, 0))
    for layer in data.visible_layers:
        if isinstance(layer, pytmx.TiledTileLayer):
            for x, y, gid in layer:
                image = data.get_tile_image_by_gid(gid) if gid else None
                if image:
                    full.blit(image, (x * data.tilewidth, y * data.tileheight))
    size = (int(full.get_width() * scale), int(full.get_height() * scale))
    pygame.image.save(pygame.transform.smoothscale(full, size) if scale != 1 else full, png_path)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Generate a Tiled map from a mapgen spec.")
    parser.add_argument("spec", help="path to a spec .yaml (see space/assets/maps/specs)")
    parser.add_argument("--seed", type=int, help="override the spec seed to re-roll the layout")
    parser.add_argument("--out", help="output .tmx path (default: assets/maps/<name>.tmx)")
    parser.add_argument("--preview", help="also render the whole map to this .png")
    args = parser.parse_args(argv)

    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    import pygame
    pygame.init()
    pygame.display.set_mode((1, 1))

    spec = load_spec(args.spec if os.path.exists(args.spec) else resolve_game_path(args.spec))
    write_extras()
    out, grid = generate(spec, seed=args.seed, out=args.out)
    print(f"Wrote {out} ({grid.width}x{grid.height}, {len(grid.rooms)} rooms, "
          f"{len(grid.objects)} interactables, spawn {grid.spawn})")
    if args.preview:
        render_preview(out, args.preview)
        print(f"Preview: {args.preview}")


if __name__ == "__main__":
    main()
