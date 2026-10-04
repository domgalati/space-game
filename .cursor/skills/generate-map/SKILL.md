---
name: generate-map
description: >-
  Designs and generates a walkable Tiled map for a planet or station in this
  repo. Grills on lore, layout, rooms, people, economy, and wiring before
  running mapgen. Use when the user asks to make, generate, or design a map,
  planet surface, or station interior, or invokes /generate-map.
disable-model-invocation: true
---

# Generate a map

Build a location with `python -m mapgen`, then wire it into the game only as far as the user asked. Grill first. Do not generate, overwrite a map, or edit game data until the answers below are settled.

Run commands with the repo venv from the repository root. The package is an editable install, so `python -m mapgen` works from that root.

## Grill

Use the AskQuestion tool when it is available. Skip a question the user already answered in this conversation. If `space/assets/maps/specs/<slug>.yaml` already exists, read it and only ask what is missing or what they want to change.

Ask, in this order:

1. **Identity.** Which body? Find its entry in `space/star_systems/*.json`: its `id` (e.g. `nexum-astra`; the game knows it as `<system>/<id>`, e.g. `sol/nexum-astra`) and its `name`. Scan and dock find the map through the entry's `map` path, not the name.
2. **Lore.** What is this place (trade hub, free port, seat of government, mining colony, farm town) and which guild runs it?
3. **Layout.** `station` (ring corridor, rooms on the rim, stars outside) or `surface` (walled compounds on open ground, joined by paths). For a surface, the `palette`: `badlands` or `urban`. Size: small 60x40, medium 100x70, or large 180x120.
4. **Rooms.** Which of `market`, `docking_bay`, `cantina`, `command`, and how many. On a station, one room may be `at: hub` (the market, unless they say otherwise).
5. **People.** Job and headcount. Existing jobs: Miner, Foreman, Security, Dockworker, Politician. New jobs need a class, a sprite, and a goods bias (see [reference.md](reference.md)).
6. **Economy.** Which goods and two or three price events, or "no market."
7. **Wiring.** Full (map, dock, market, talk lines), dockable only, or map file only.
8. **Flavor,** only if wiring is full. Hail line, and what the bar and command console say. Otherwise keep the stock lines.

State these limits while asking, do not ask them as if they were choices:

- A station is always open space with stars outside the hull. A surface is always open ground joined by paths. Surface palettes: `badlands` (Terramonta look: dark red ground, dirt paths, red shrubs, orange rocks) and `urban` (concrete city blocks and asphalt roads around the compounds, bare gray rock beyond). There is no terran or industrial palette yet.
- Hand edits in Tiled are lost the next time the spec is regenerated.

Save every answer into the spec, including lore, so the next run does not re-ask settled questions. Copy [spec.template.yaml](spec.template.yaml) to `space/assets/maps/specs/<slug>.yaml`.

## Generate

Before writing the real map, check the destination `space/assets/maps/<name>.tmx`:

- Missing: fine to create.
- Present and `python .cursor/skills/generate-map/scripts/smoke_map.py "<map>"` exits 2: it is hand-made (no `mapgen_seed`). Stop and ask. Never regenerate it.
- Present and the smoke script exits 0 or 1: it is generated. Warn that regenerating wipes Tiled edits, then continue only if the user agrees.

Offer three seeds before committing to one. Write each preview somewhere temporary, not over the real map:

```bash
python -m mapgen space/assets/maps/specs/<slug>.yaml --seed <N> --out <tmp>/<name>.tmx --preview <tmp>/<name>-<N>.png
```

Show the three previews and let the user pick. Put the chosen seed in the spec, then generate the real map with no `--out` and no `--seed` override:

```bash
python -m mapgen space/assets/maps/specs/<slug>.yaml --preview <tmp>/<name>.png
```

Show that preview. Then run:

```bash
python .cursor/skills/generate-map/scripts/smoke_map.py "space/assets/maps/<name>.tmx"
```

Fix the spec and regenerate if it fails. Do not hand-edit the `.tmx` to silence the script.

## Wire

Match the wiring answer. Details and file pointers are in [reference.md](reference.md).

- **Map only.** Spec and `.tmx` only.
- **Dockable.** Write the map, then set the body's `"map": "space/assets/maps/<name>.tmx"` in the star-system JSON; landing is "the body names a map that exists." A station object needs a `guild` or the scan readout omits it. Do not change which body the game boots into unless the user asks.
- **Full.** Also add an `economy.yaml` entry keyed by the body's full id (`sol/nexum-astra:`), `JOB_GOODS_BIAS` lines for any new job, and new NPC classes. Goods are item ids from `space/items.yaml` (`raw-minerals`, not `Raw Minerals`); a new good needs an entry there first. Do not invent goods the user did not agree to.

Commit only when the user asks.

## Limits

Room types the furnisher knows: `market`, `docking_bay`, `cantina`, `command`, `housing`. Any other `type` still gets a room, with generic lockers and panels. Themes: `station`, `surface`. Adding a room, a prop, or a theme is in [reference.md](reference.md). Do that only when the grill turns up something the generator cannot build.
