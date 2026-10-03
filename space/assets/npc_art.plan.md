# Planetary NPC art plan

Audited 2026-10-03 on `npc-art`. The inventory below records the state before this art pass.

Implementation update: the user approved all 15 species/job world sprites and Hesk, reviewed their native scale on Terramonta, and authorized integration. All 16 are installed under `space/assets/img/npcs/`, with species/job selection and Hesk's explicit override connected. Dialogue portraits remain unchanged. All 193 tests pass; all 42 NPCs and their dialogue portraits rendered successfully across the three current maps. Portrait refinement and future faction batches remain separate work.

## Findings

The current implementation has **five jobs, three species, and one implemented NPC faction**, giving **15 supported species/job combinations**, plus one authored character. There are five map sprites, all human-shaped, selected by job alone. Species is visible in dialogue portraits but not on the map.

Every current job has a sprite file. All **75 portrait layer PNGs** referenced by the manifest exist and are 64×64. The gap is species representation, role clarity, individual variety, and replacement of explicitly labeled portrait placeholders—not missing files for additional implemented job classes.

Sources:

- `space/src/entities/npcs/assembly_npc.py`: Miner, Foreman, Dockworker, Security, Politician.
- `space/src/entities/npcs/species.py`: Human (70% generation weight), Vessari (15%), Muroth (15%). Species selection is independent of job. Alien names and lore are explicitly provisional.
- `space/src/entities/npcs/npc_generator.py`: explicit character sprite → job-class sprite → dockworker fallback. Species does not affect map sprite selection.
- `space/src/modes/planetary_mode/npc_manager.py`: map populations, authored-character posts, static sprite loading and drawing.
- `space/assets/img/portraits/manifest.yaml` and `space/tools/gen_portrait_placeholders.py`: modular portrait art and its placeholder status.
- `space/characters/hesk_durran.yaml`: authored Muroth Foreman, without a custom map sprite.

## Current population and art coverage

| Job | Human map art | Vessari map art | Muroth map art | Portrait outfit | Where used today |
|---|---|---|---|---|---|
| Miner | Present; red workwear, helmet, pickaxe | Uses human Miner | Uses human Miner | Present, placeholder | Terramonta ×6; Etheora ×10 |
| Foreman | Present; white shirt and hard hat | Uses human Foreman | Uses human Foreman | Present, placeholder | Terramonta ×6; Etheora ×3; Hesk separately |
| Dockworker | Present; green miner-like silhouette and pickaxe | Uses human Dockworker | Uses human Dockworker | Present, placeholder | Etheora ×6; Nexum Astra ×5 |
| Security | Present; blue miner-like silhouette and pickaxe | Uses human Security | Uses human Security | Present, placeholder | Nexum Astra ×3 |
| Politician | Present; purple foreman-like silhouette and hard hat | Uses human Politician | Uses human Politician | Present, placeholder | Nexum Astra ×2 |

Terramonta uses the industrial fallback of six Miners and six Foremen, plus Hesk's character post: **13 NPCs**. Etheora specifies **19 NPCs**; Nexum Astra specifies **10 NPCs**. This is **41 procedural residents plus Hesk**, across the three available named destination maps. Explicit map counts and authored characters are not clamped to the nominal 12-NPC fallback cap.

Fresh deterministic rosters currently generate **15 alien procedural residents** across those maps, plus Hesk. Existing saved rosters may differ. Even combinations absent from these initial rosters remain supported and need coverage.

`Terramonta_old.tmx` and `Terramonta_new_art.tmx` are alternate files; planetary mode loads the destination's exact name. Other planets in `sol.json` lack corresponding map files here and are not additional live surface populations.

### Portrait inventory

| Layer | Existing PNGs | Coverage |
|---|---:|---|
| Head | 3 | One per species |
| Eyes | 13 | Five eye variants with separate iris/glow/brow parts |
| Mouth | 10 | Species mouths plus Muroth tusks |
| Back hair | 4 | Human long/shoulder; Muroth mane/braids |
| Front hair | 11 | Six human styles, Muroth topknot, four Vessari crests |
| Facial hair | 4 | Human beard, mustache, goatee, stubble |
| Outfit | 13 | Five jobs plus default; base/accent pairs, extra Dockworker detail |
| Accessory | 17 | Goggles, scar, eyepatch, cybereye, earpiece for all species; earrings for Human/Muroth |
| **Total** | **75** | All manifest references resolve locally |

Missing combinations such as Vessari facial hair are intentional manifest restrictions, not automatically missing art. Palette variations also do not require separate PNGs.

## Production plan

### 1. Establish one shared visual reference

Before producing the full set, compare a Human, Vessari, and Muroth in the same job at actual map size, alongside their dialogue portraits. Use existing species designs as the starting point: slender, cool-toned Vessari with crests; broad, warm-toned Muroth with ears and tusks. These are current placeholder cues, not finalized lore.

Choose consistent proportions, lighting, outline, clothing, and Assembly accent treatment. Keep species recognizable through silhouette and facial structure, and jobs through clothing/equipment rather than color alone. Check the samples against Terramonta's terrain, Etheora's streets, and Nexum Astra's interiors.

Deliverable: a reference sheet with three species and five role designs, plus native-size examples. Resolve species design changes here before investing in replacement portrait layers.

### 2. Close map coverage first

Minimum addition: **10 new static 24×24 transparent sprites**, retaining the five human sprites initially.

| New sprite pair | Quantity | Priority and design brief |
|---|---:|---|
| Vessari/Muroth Foreman | 2 | First: covers Terramonta, Etheora, and provides Hesk's base. Supervisor jacket or shirt, clipboard/tablet; retain species silhouette. |
| Vessari/Muroth Miner | 2 | First: common industrial residents. Protective workwear, helmet shaped around species anatomy, compact mining tool. |
| Vessari/Muroth Dockworker | 2 | Next: present on two destinations. Cargo harness, work gloves, scanner or handling tool. |
| Vessari/Muroth Security | 2 | Next: armored or uniformed guard, comms/badge, clear patrol silhouette. |
| Vessari/Muroth Politician | 2 | Next: formal civilian clothing and insignia, distinct from industrial workers. |

In the same production pass, **revise five existing human sprites** to match the approved designs. Dockworker, Security, and Politician need the strongest changes: pickaxes and construction helmets currently obscure their roles. Miner and Foreman may need only consistency adjustments after review.

Target: **15 coherent species/job sprites**. The net increase is ten files, even if all fifteen designs receive art work. Reuse shared body/clothing components during authoring where useful; exported flat PNGs fit today's renderer.

### 3. Give Hesk a recognizable map identity

Add **one named-character sprite** derived from the Muroth Foreman, with topknot, goggles, tusks, and the existing warm skin palette. Set an explicit `sprite` in `hesk_durran.yaml` when integrating it.

His portrait already has pinned topknot, stern mouth, goggles, skin/hair/eye colors, and no back hair. Retain that recipe for the first pass; a unique full portrait is optional. His remaining unpinned selections are deterministic for his character ID.

Target after this phase: **16 map sprites total**, including Hesk. This is **11 new map assets plus up to five revisions**.

### 4. Refine the modular portraits

Treat this as a quality pass over existing coverage, not 15 unrelated commissioned portraits. Review all 75 layers and replace only the parts that fail the approved style; a complete replacement would be 75 layer files, not 75 portraits.

Suggested order:

1. Three heads, five eye variants, and mouth/tusk parts: establish readable, distinct species.
2. Five job outfits and the default outfit, preserving accent masks: align their uniforms with the map sprites. Check neck/shoulder fit on all three heads before deciding whether species-specific outfit parts are necessary.
3. Hair/crests and accessories: validate alignment, layering, and clipping across eligible combinations.
4. Population variety: add head shapes, hair, age cues, and outfit wear only after basic consistency works. Additional variants need an explicit scope and count; do not multiply every job by every portrait color.

Use the existing `default` outfit for unknown jobs. A dedicated neutral civilian map sprite is an optional follow-up because unknown jobs currently appear as Dockworkers; no named civilian job is authored today.

### 5. Keep future factions as a separate batch

`space/assets/pirates.plan.md` proposes **Caravan Master, Trader, Navigator, Rigger, and Outrider**. These are proposed jobs, not implemented NPC classes or current map populations. Etheora's checked-in spec and TMX still say Assembly.

Once those roles are adopted, budget **15 species/job map sprites** for full three-species coverage, and **five portrait outfit variants**. Following the present base-plus-accent pattern would mean approximately **10 new outfit PNGs**, with additional species tailoring only if fitting requires it. Shared heads/hair/accessories can be reused. The earlier pirate plan's five recolored sprites would supply job coverage but repeat today's species gap.

Caravaneer orange, Cohort green, and Dominion red already exist as portrait accent colors. Only Assembly has a runtime NPC module here. Palette entries alone do not imply implemented faction NPCs; budget no speculative Cohort or Dominion job sets yet. Space-mode pirate ship art is outside this plan.

## Integration needed to display the new art

- Introduce an explicit map-sprite lookup by **guild + job + species** in or beside `npc_generator.py`. Preserve authored `record['sprite']` overrides and a deliberate fallback for unknown content. Simply adding files will not change today's job-only selection.
- Suggested new asset layout: `space/assets/img/npcs/assembly/<species>/<job>.png`, plus `space/assets/img/npcs/characters/hesk_durran.png`. This is a proposed layout; existing assets currently live in `img/objects/`.
- Keep the first pass static. `NPCManager` blits a single loaded image without scaling or frame selection, and `TILE_SIZE` is 24. Walk cycles, directional sheets, and animated idle poses require a separate renderer change and are not prerequisites for coverage.
- Use **24×24 RGBA PNGs**, consistent foot alignment, and a silhouette contained in one tile. Check crests, ears, helmets, and tools against tile edges.
- Keep portrait layers **64×64 transparent PNGs**, aligned around x=32; the manifest specifies 4× display. Tintable parts stay grayscale so the existing skin/hair/eyes/accent multiplication works. Preserve layer order and variant IDs used by saved recipes and Hesk.
- Avoid rerunning `gen_portrait_placeholders.py` over finished portrait art: it writes the placeholder layer paths. Change its output policy or retire that generation step when replacing those assets.
- Check new raster assets are included in the eventual change. The README warns that not all game raster assets have historically been tracked.

## Acceptance checks

1. A contact sheet shows every one of the 15 species/job pairs and Hesk, with map sprites at native size and enlarged, next to portraits.
2. Each species is recognizable at 24×24; each job is readable without relying only on hue. Hesk is distinguishable from a generic Muroth Foreman.
3. All new paths resolve, map sprites are 24×24 with transparency, and portrait layers remain aligned 64×64 assets.
4. Sprite-selection checks cover all 15 combinations, an authored override, unknown-job fallback, and a saved record without an explicit sprite.
5. Run existing portrait, roster, and character-content tests. Check the manifest's full layer set for missing files and render eligible combinations to catch clipping that file-existence tests cannot catch.
6. Inspect Terramonta, Etheora, and Nexum Astra in game; open dialogue with each species, verify portrait/map agreement, and revisit or reload to confirm stable appearance.

Recommended first deliverable: **the three-species Foreman comparison plus Hesk**, then extend the accepted designs to the other four jobs. This resolves the species design and named-character needs before the full production batch.

## Audit validation

Inspected an enlarged contact sheet of all five existing map sprites, 15 composed species/job portraits, and Hesk. Verified five 24×24 map images and all 75 unique manifest-referenced portrait files locally. Existing portrait, roster, and character-content tests: **18 passed**. The first sandboxed run encountered temporary-directory permissions; the authorized rerun passed, with dependency-deprecation and pytest-cache permission warnings. No in-game visual playtest was performed for this planning-only change.
