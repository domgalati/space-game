# Remaining planetary NPC samples — v1

Thirteen approval candidates: four jobs × three species, plus Hesk Durran. The three Foreman samples in `../foreman-v1/` were previously approved and remain unchanged.

**Approved and integrated on 2026-10-03**, after the user reviewed the Terramonta scale preview and explicitly authorized wiring them in. Production copies live under `../../assembly/` and `../../characters/`; dialogue portraits are unchanged. Review-sheet captions retain their historical pre-approval wording.

## Review sheets

- [Miners and Dockworkers](approval-workers.png): M1–M3 and D1–D3.
- [Security and Politicians](approval-civic.png): S1–S3 and P1–P3.
- [Hesk beside the approved Muroth Foreman](approval-hesk.png): H1.

Each sheet shows an 8× nearest-neighbor preview and the actual 24×24 export beneath it. Review the final exports, not the higher-resolution generated sources.

| ID | Candidate | Production-format file | Approval |
|---|---|---|---|
| M1 | miner-human | [PNG](miner-human-v1.png) | Approved |
| M2 | miner-vessari | [PNG](miner-vessari-v1.png) | Approved |
| M3 | miner-muroth | [PNG](miner-muroth-v1.png) | Approved |
| D1 | dockworker-human | [PNG](dockworker-human-v1.png) | Approved |
| D2 | dockworker-vessari | [PNG](dockworker-vessari-v1.png) | Approved |
| D3 | dockworker-muroth | [PNG](dockworker-muroth-v1.png) | Approved |
| S1 | security-human | [PNG](security-human-v1.png) | Approved |
| S2 | security-vessari | [PNG](security-vessari-v1.png) | Approved |
| S3 | security-muroth | [PNG](security-muroth-v1.png) | Approved |
| P1 | politician-human | [PNG](politician-human-v1.png) | Approved |
| P2 | politician-vessari | [PNG](politician-vessari-v1.png) | Approved |
| P3 | politician-muroth | [PNG](politician-muroth-v1.png) | Approved |
| H1 | hesk-durran | [PNG](hesk-durran-v1.png) | Approved |

## Format and art direction

Every candidate is a separate 24×24 RGBA PNG, uses binary transparency (0/255), and has at most eight opaque colors. Feet share a baseline with one transparent row below. These are static world sprites in the approved low-bit NES-like style; not ASCII art, animated sheets, or dialogue portraits. This is an aesthetic target rather than literal NES hardware palette compliance.

Role cues: Miners have rust-red overalls and a short pick; Dockworkers have olive workwear, a safety harness and scanner; Security wears slate/navy armor; Politicians wear plum formal coats. Species cues follow the approved Foremen. Hesk adds cyan work goggles to the Muroth Foreman design.

## Provenance and reproduction

Created with the built-in `image_gen` tool, one request per asset, referencing the approved Foreman sheet. Exact prompts are in [generation.json](generation.json). Unmodified tool outputs are retained in `sources/`. [export.cjs](export.cjs) mechanically crops, downsamples with nearest-neighbor sampling, applies a limited palette and binary alpha, and creates review sheets. It does not draw character artwork.

Run `node export.cjs <sharp-module-path>` from this directory; source paths are recorded in `source-files.json`. [validation.json](validation.json) records each export's format, palette, source crop and hash. All 13 passed Pygame loading and direct checks of dimensions, RGBA mode, binary alpha, palette size, clear top/bottom margins and file hashes. The final approval sheets were visually reviewed. These checks establish asset-format compatibility; the sprites have not been playtested in the game.

The procedural species/job lookup is now implemented in `entities/npcs/sprites.py` and used by `build_npc`. Hesk has an explicit character sprite override. All three mapped destinations passed a headless rendering check after integration.
