from pathlib import Path

import pygame
import pytest

from entities.npcs.portrait import PORTRAIT_DIR, compose, load_manifest, portrait_surface, roll_appearance
from entities.npcs.species import SPECIES
from util.config import resolve_game_path


def test_every_manifest_file_exists():
    manifest = load_manifest()
    root = Path(resolve_game_path(PORTRAIT_DIR))
    missing = []
    for layer, spec in manifest["layers"].items():
        for variant in spec["variants"]:
            for species in variant.get("species", SPECIES):
                for part in variant["parts"]:
                    if "species" in part and species not in part["species"]:
                        continue
                    relative = part["file"].format(species=species)
                    if not (root / relative).exists():
                        missing.append(f"{layer}/{variant['id']}: {relative}")
    assert missing == []


@pytest.mark.parametrize("species", list(SPECIES))
def test_roll_is_deterministic_and_species_appropriate(species):
    manifest = load_manifest()
    recipe = roll_appearance("A/Miner-01", species, "Miner", "assembly")
    assert recipe == roll_appearance("A/Miner-01", species, "Miner", "assembly")
    assert recipe["colors"]["skin"] in manifest["palettes"]["skin"][species]
    assert recipe["colors"]["accent"] == manifest["palettes"]["accent"]["assembly"]
    for layer, variant_id in recipe["layers"].items():
        if variant_id is None:
            continue
        variant = next(v for v in manifest["layers"][layer]["variants"] if v["id"] == variant_id)
        assert species in variant.get("species", [species])


def test_outfit_follows_job_with_default_fallback():
    assert roll_appearance("x", "human", "Politician", "cohort")["layers"]["outfit"] == "politician"
    assert roll_appearance("x", "human", "Bartender", "cohort")["layers"]["outfit"] == "default"
    assert roll_appearance("x", "human", "Miner", "nobody")["colors"]["accent"] == "#8e9eac"


def test_fixed_overrides():
    recipe = roll_appearance(
        "character:test", "muroth", "Foreman", "assembly",
        fixed={"colors": {"skin": "#010203"}, "layers": {"accessory": "goggles", "back_hair": "none"}},
    )
    assert recipe["colors"]["skin"] == "#010203"
    assert recipe["layers"]["accessory"] == "goggles"
    assert recipe["layers"]["back_hair"] is None


def test_compose_and_scale():
    recipe = roll_appearance("A/Foreman-01", "human", "Foreman", "assembly")
    base = compose(recipe)
    assert base.get_size() == (64, 64)
    assert base.get_at((32, 25)).a == 255  # the face is there
    assert portrait_surface(recipe, 256).get_size() == (256, 256)
    assert compose(recipe) is base


def test_compose_tolerates_unknown_variants():
    recipe = roll_appearance("A/Miner-02", "human", "Miner", "assembly")
    recipe["layers"]["front_hair"] = "no_such_hair"
    assert isinstance(compose(recipe), pygame.Surface)
