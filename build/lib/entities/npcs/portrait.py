"""Layered NPC portraits: roll a recipe once per NPC, then composite it on demand.

The layer spec lives in space/assets/img/portraits/manifest.yaml.
"""
import json
import random
import zlib
from functools import lru_cache
from pathlib import Path

import pygame
import yaml

from util.config import resolve_game_path

PORTRAIT_DIR = "space/assets/img/portraits"

_image_cache = {}
_composite_cache = {}
_scaled_cache = {}
_warned = set()


@lru_cache(maxsize=1)
def load_manifest():
    with open(Path(resolve_game_path(PORTRAIT_DIR)) / "manifest.yaml", "r", encoding="utf-8") as file:
        return yaml.safe_load(file)


def _eligible(variant, species, job):
    if "species" in variant and species not in variant["species"]:
        return False
    if "jobs" in variant and job not in variant["jobs"]:
        return False
    return True


def _pick_variant(rng, spec, species, job):
    variants = [v for v in spec["variants"] if _eligible(v, species, job)]
    if spec.get("pick") == "job":
        for variant in variants:
            if job in variant.get("jobs", ()):
                return variant["id"]
        return "default" if any(v["id"] == "default" for v in variants) else None
    options = [v["id"] for v in variants] + [None]
    weights = [v.get("weight", 1) for v in variants] + [spec.get("none", 0)]
    if not sum(weights):
        return None
    return rng.choices(options, weights=weights)[0]


def _pick_color(rng, palette, species):
    if isinstance(palette, dict):
        palette = palette.get(species) or palette.get("default") or ["#ffffff"]
    return rng.choice(palette)


def roll_appearance(npc_id, species, job, guild, fixed=None):
    """
    A recipe ({species, colors, layers}) rolled from ``npc_id``. ``fixed`` pins parts of it, e.g.
    {"colors": {"skin": "#c98f68"}, "layers": {"front_hair": "mohawk", "accessory": "none"}}.
    """
    manifest = load_manifest()
    palettes = manifest["palettes"]
    rng = random.Random(zlib.crc32(f"portrait:{npc_id}".encode("utf-8")))
    colors = {
        "skin": _pick_color(rng, palettes["skin"], species),
        "hair": _pick_color(rng, palettes["hair"], species),
        "eyes": _pick_color(rng, palettes["eyes"], species),
        "accent": palettes["accent"].get(guild) or palettes["accent"]["default"],
    }
    layers = {layer: _pick_variant(rng, manifest["layers"][layer], species, job) for layer in manifest["order"]}
    if fixed:
        colors.update(fixed.get("colors") or {})
        for layer, variant in (fixed.get("layers") or {}).items():
            layers[layer] = None if variant in (None, "none") else variant
    return {"species": species, "colors": colors, "layers": layers}


def _hex(color):
    if isinstance(color, (list, tuple)):
        return tuple(int(c) for c in color[:3])
    value = color.lstrip("#")
    return tuple(int(value[i:i + 2], 16) for i in (0, 2, 4))


def _warn(message):
    if message not in _warned:
        _warned.add(message)
        print(f"[portrait] {message}")


def _load(relative):
    if relative not in _image_cache:
        path = Path(resolve_game_path(PORTRAIT_DIR)) / relative
        try:
            _image_cache[relative] = pygame.image.load(str(path))
        except (FileNotFoundError, pygame.error):
            _warn(f"missing layer image {relative}")
            _image_cache[relative] = None
    return _image_cache[relative]


def _tinted(image, color):
    tinted = image.copy()
    tinted.fill((*color, 255), special_flags=pygame.BLEND_RGBA_MULT)
    return tinted


def _variant(manifest, layer, variant_id):
    for variant in manifest["layers"].get(layer, {}).get("variants", []):
        if variant["id"] == variant_id:
            return variant
    _warn(f"unknown {layer} variant {variant_id!r}")
    return None


def compose(recipe):
    """The native-size (64x64) portrait for ``recipe``."""
    key = json.dumps(recipe, sort_keys=True)
    if key in _composite_cache:
        return _composite_cache[key]
    manifest = load_manifest()
    size = manifest["size"]
    species = recipe["species"]
    surface = pygame.Surface((size, size), pygame.SRCALPHA)
    for layer in manifest["order"]:
        variant_id = recipe["layers"].get(layer)
        variant = _variant(manifest, layer, variant_id) if variant_id else None
        if not variant:
            continue
        for part in variant["parts"]:
            if "species" in part and species not in part["species"]:
                continue
            image = _load(part["file"].format(species=species))
            if image is None:
                continue
            tint = part.get("tint")
            if tint:
                image = _tinted(image, _hex(recipe["colors"][tint]))
            surface.blit(image, (0, 0))
    _composite_cache[key] = surface
    return surface


def portrait_surface(recipe, size):
    """``recipe`` composited and scaled to ``size`` pixels square with hard pixel edges."""
    key = (json.dumps(recipe, sort_keys=True), size)
    if key not in _scaled_cache:
        _scaled_cache[key] = pygame.transform.scale(compose(recipe), (size, size))
    return _scaled_cache[key]
