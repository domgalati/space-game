# Foreman species samples, v1

Three approval candidates for planetary mode, created 2026-10-03. Each final sprite is a **24×24 RGBA PNG** with binary transparency and no antialiasing, using at most eight opaque colors. This is a limited-palette NES-like interpretation, not a claim of literal NES hardware palette compliance.

| Review ID | Species | Asset | Opaque colors |
|---|---|---|---:|
| A | Human | `human-foreman-v1.png` | 7 |
| B | Vessari | `vessari-foreman-v1.png` | 8 |
| C | Muroth | `muroth-foreman-v1.png` | 8 |

`approval-sheet.png` compares the existing Foreman with the three candidates at 8× nearest-neighbor size and actual 1× size. Approve/reject the 24×24 export shown on this sheet; the larger generated sources are only source material.

The job is Foreman for all three: pale work shirt, dark trousers, and a compact industrial silhouette. The human wears a hard hat, Vessari has a crest and cool skin, and Muroth has a broad head, ears, tusks, and a topknot. A one-pixel top and bottom margin keeps the figures within a tile. Hesk is not depicted as a separate named character in this batch.

Generated using the built-in image_gen tool. Full prompts are in `prompts.md`; unmodified generated outputs are preserved in `sources/`. `export.cjs` performs the size, transparency, and palette conversion; `validation.json` records the exports. No character pixels are procedurally drawn by the exporter.

All three samples were approved and integrated on 2026-10-03. Production copies live under `../../assembly/<species>/foreman.png`; the review-sheet caption reflects the earlier review stage. An approved file can be loaded directly by Pygame and used through an explicit character `sprite` path. Procedural species-specific selection is implemented in `entities/npcs/sprites.py`.

To reproduce with Node and Sharp available:

```text
node export.cjs <sharp-module-path> sources/human-generated.png sources/vessari-generated.png sources/muroth-generated.png
```

The exporter retains the sources and writes outputs in this directory. Visual review of the exact exports and image-format checks completed; all three mapped destinations passed a headless rendering check after integration.
