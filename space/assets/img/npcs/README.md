# Planetary NPC world sprites

Approved and integrated on 2026-10-03. Production files are byte-for-byte copies of the approved 24×24 transparent PNG samples; dialogue portrait assets are unchanged.

- `assembly/<species>/<job>.png`: Human, Vessari and Muroth versions of Miner, Foreman, Dockworker, Security and Politician (15 assets).
- `characters/hesk_durran.png`: Hesk's dedicated Muroth Foreman with cyan goggles.
- `samples/`: retained source generations, prompts, exported candidates and historical approval sheets. Their pending/not-installed captions describe the review stage, before integration was authorized.

`entities/npcs/sprites.py` registers the species/job paths. `build_npc` selects an explicit record sprite first, then registered species/job art, then the class sprite and default human Dockworker. An unknown species uses its job's human sprite. Unregistered guilds/jobs retain the class/default fallback.

Sprites resolve when residents are built, so stored records without a sprite override receive current art without changing names, portraits, or world state. Hesk's character YAML pins his dedicated sprite. Approved samples are preserved; regenerating a sample does not overwrite production assets.

Validation: 193 tests passed, including coverage for all 15 combinations, exact agreement with approved image files, sprite overrides and saved-roster loading. A headless PlanetaryMode smoke check loaded all 42 NPC sprites across Terramonta, Etheora and Nexum Astra, drew each destination's starting view, and rendered every NPC's dialogue portrait. The integrated Terramonta screenshot is `screenshots/terramonta-npc-integrated-1080x720.png`.
