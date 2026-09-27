# Mapgen reference

Read this only when wiring a generated map or extending the generator. The workflow is in [SKILL.md](SKILL.md).

## What the generator writes

`python -m mapgen <spec.yaml> [--seed N] [--out map.tmx] [--preview map.png]`

Specs live in `space/assets/maps/specs/`. The default output is `space/assets/maps/<name>.tmx`. Map properties:

| Property | Meaning |
|---|---|
| `guild` | Passed to NPC generation, ahead of the body's guild |
| `npc_jobs` | `Security:3,Dockworker:5` headcounts |
| `mapgen_theme` | `station` or `surface` |
| `mapgen_seed` | Present only on generated maps. Absence means hand-made |

Object layers, all hidden: `Objects` (interactables), `NPC Posts` (job, tile), `Spawns` (`Player Start`). The `walkable` layer is any non-zero gid. Props are solid because their footprint is removed from `walkable`.

`load_spec` ignores unknown keys, so a `lore` block stays in the yaml and is not written into the tmx.

## Stock lines

Scan and hail already treat any body with a matching `.tmx` as landable (`has_landing_map` in `space/src/modes/star_system_mode/scan_terminal.py`). Stations get a generic dockmaster hail. Change that only when the user supplied a line.

`Bar Counter` and `Command Console` are handled in `InteractionManager.handle_interaction_with`. The bar rumor is built from real prices. The console says it is restricted to Assembly staff.

## Wiring checklist

**Economy.** Add a sibling of `Terramonta` in `space/src/util/economy/economy.yaml`: `goods` with `basePrice` and `currentPrice`, and `events` whose keys are those goods and whose values are `priceChange: "+20%"` style strings. `Economy.fire_event` crashes if the location is missing.

**New job.** Three edits, all required:

1. A class in `space/src/entities/npcs/assembly_npc.py` with `self.sprite` pointing at `space/assets/img/objects/<job>.png`. `generate_npc` imports `{guild}_npc`, so the class name is the job name.
2. A 24x24 sprite. Recolor `miner.png` or `foreman.png`. Do not crop the MAS character sheet; those sprites are a different style and a different scale.
3. A `JOB_GOODS_BIAS` entry in `space/src/modes/planetary_mode/interaction_manager.py`. Goods must exist in this location's economy or the talk line is skipped.

Posts come from the map. `NPCManager` hangs each NPC near up to two of its job's posts. No code change per location unless the job is new.

**Star system JSON.** A station is an `objects` entry and needs `guild` or scan omits it. A planet already has `type` and `guild`. Do not add `start_pos`; generated maps spawn from `Player Start`.

## Adding a room type

In `space/src/mapgen/themes/station.py`:

1. Add a floor style to `FLOORS` and a `ROOM_FLOOR` entry.
2. Add a `(min_w, max_w), (min_h, max_h)` pair to `ROOM_SIZE`.
3. Write a furnisher and register it in `FURNISH`.

Place solid props with `grid.place(stamp, x, y, keep_clear)` and interactables with `grid.add_object(name, x, y, stamp=...)`. Both refuse a placement that cuts the floor in two. `grid.room_keep_clear(room)` is the cells in front of the doors. `add_posts(grid, job, cells)` writes NPC posts. The surface theme calls the same `FURNISH` table, so a new room works on both themes.

## Adding a prop

Add a `Stamp(sheet, row, col, width, height)` to `STAMPS` in `space/src/mapgen/tiles.py`. `sheet` is `tileset`, `space`, or `roguelike` (see `SHEET_FILES`). `row` and `col` are 24px cells on that sheet. The next generate copies the block into `mapgen_extras.png` and keys out the black backdrop from the edges, so props sit on any floor. Inner black outlines are kept.

## Adding a theme

New module under `space/src/mapgen/themes/` with `generate(spec, rng) -> (grid, background)`, registered in `THEMES`. `background` maps `(x, y)` to a gid for the bottom layer. Call `grid.derive_walls()` only when walls should seal every floor edge; the surface theme draws its own compound walls and must not.
