from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace

import pygame
import pytest

from entities.npcs.npc import NPC
from entities.npcs.npc_generator import DEFAULT_SPRITE, build_npc, roll_npc_record
from entities.npcs.sprites import map_sprite
from util.config import resolve_game_path
from world.characters import character_record, load_character
from world.roster import NPCRoster
from world.world_state import WorldState


@pytest.mark.parametrize("species", ["human", "vessari", "muroth"])
@pytest.mark.parametrize("job", ["Miner", "Foreman", "Dockworker", "Security", "Politician"])
def test_each_species_job_loads_the_exact_approved_art(species, job):
    record = roll_npc_record("art-check", job, "assembly")
    record["species"] = species
    npc = build_npc(record)
    expected = f"space/assets/img/npcs/assembly/{species}/{job.lower()}.png"
    assert npc.sprite == expected
    path = Path(resolve_game_path(npc.sprite))
    if job == "Foreman":
        sample = f"foreman-v1/{species}-foreman-v1.png"
    else:
        sample = f"roster-v1/{job.lower()}-{species}-v1.png"
    assert path.read_bytes() == Path(resolve_game_path(f"space/assets/img/npcs/samples/{sample}")).read_bytes()
    image = pygame.image.load(str(path))
    assert image.get_size() == (24, 24)
    colors = {tuple(image.get_at((x, y))) for x in range(24) for y in range(24)}
    assert {color[3] for color in colors} == {0, 255}
    assert len({color[:3] for color in colors if color[3]}) <= 8


def test_authored_sprite_override_wins():
    record = roll_npc_record("custom", "Miner", "assembly")
    record.update(species="vessari", sprite="custom/unique.png")
    assert build_npc(record).sprite == "custom/unique.png"


def test_hesk_uses_approved_named_sprite():
    npc = build_npc(character_record(load_character("hesk_durran")))
    assert npc.sprite == "space/assets/img/npcs/characters/hesk_durran.png"
    assert Path(resolve_game_path(npc.sprite)).read_bytes() == Path(resolve_game_path(
        "space/assets/img/npcs/samples/roster-v1/hesk-durran-v1.png"
    )).read_bytes()


@pytest.mark.parametrize("species", [None, "unrecognized-species"])
def test_legacy_or_unknown_species_keeps_job_art(species):
    record = roll_npc_record("legacy", "Security", "assembly")
    if species is None:
        del record["species"]
    else:
        record["species"] = species
    assert build_npc(record).sprite == "space/assets/img/npcs/assembly/human/security.png"


def test_unknown_job_gets_default_art():
    record = roll_npc_record("unknown", "Bartender", "assembly")
    assert build_npc(record).sprite == DEFAULT_SPRITE
    assert map_sprite("caravaneers", "Miner", "human") is None


def test_unregistered_guild_keeps_its_class_art(monkeypatch):
    class Visitor(NPC):
        def __init__(self):
            super().__init__()
            self.sprite = "custom/visitor.png"

    record = roll_npc_record("visitor", "Miner", "assembly")
    record.update(guild="future_guild", job="Visitor")
    monkeypatch.setattr("entities.npcs.npc_generator._guild_module", lambda guild: SimpleNamespace(Visitor=Visitor))
    assert build_npc(record).sprite == "custom/visitor.png"


def test_saved_residents_get_new_art_without_rerolling(tmp_path):
    world = WorldState(str(tmp_path / "world.yaml"))
    records = NPCRoster(world).for_location("Terramonta", {"Foreman": 6}, "assembly")
    before = deepcopy(records)
    world.save()
    loaded = WorldState.load(world.path)
    residents = NPCRoster(loaded).for_location("Terramonta", {"Foreman": 6}, "assembly")
    for record in residents:
        assert "sprite" not in record
        npc = build_npc(record)
        assert npc.sprite == f"space/assets/img/npcs/assembly/{record['species']}/foreman.png"
        assert npc.portrait_recipe == record["portrait"]
    assert residents == before
