# Terminal bezel artwork

Three separate production PNGs, designed as a family with literal TeleSys glyph decoration and flat NES-style hardware:

| Terminal | Asset | Direction |
|---|---|---|
| Ship | [ship/terminal_screen.png](ship/terminal_screen.png) | Dark petrol, ivory and cyan; navigation diagrams, segmented ribs and instrument keys. |
| Market | [market/terminal_screen.png](market/terminal_screen.png) | Olive brass and parchment; engraved ledger columns, register cassette and trade glyphs. |
| Docking | [docking/terminal_screen.png](docking/terminal_screen.png) | Slate and amber; paired mechanical clamps, caution marks and berth brackets. |

## Exact pixel contract

- Each PNG is **880×520, 8-bit RGBA**, matching `space/assets/img/objects/terminal_screen.png`.
- The source is fully opaque, including its black exterior and screen. All three preserve the complete original alpha channel; transparency was not added.
- The rounded screen opening is copied pixel-for-pixel from the source: **221,580 pixels**, bounding rectangle **[91,88,783,409)** (right and bottom exclusive).
- Its boundary is also identical: validation checks the connected screen area, preventing accidental enlargement or art intrusion.
- The terminal screen remains empty. No scanlines, reflections, decorative readouts, or labels are painted inside it.
- All lettering and glyph decorations use `space/assets/fonts/TeleSys.ttf`, rendered as native 8×16 binary masks. Titles use integer 2× nearest-neighbor magnification. Glyphs are real characters, not generated textures.
- Flat, integer-coordinate pixel shapes form the bezel and hardware. No antialiasing, blur, gradients, or fractional scaling. Each final asset uses 11–12 colors including black.

Only art files and their supporting source/metadata were created. No game code or original assets were modified and nothing is wired into the game.

## Reproduction

`generate.py` is a deterministic offline art generator using Pillow and NumPy. From the repository root, run:

```text
python space/assets/img/_style_samples/terminal_variants/generate.py
```

It writes only these three variant directories and `validation.json`. Each directory includes `glyphs.json` with the decorative glyph positions, characters, colors, and integer scales. `validation.json` records source/output hashes and the pixel contract checks. Identical source image, font, generator, and rendering dependencies produce identical output.
