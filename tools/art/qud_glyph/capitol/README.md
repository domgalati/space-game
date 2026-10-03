# Capitol station — literal glyph revision

This revision uses `GlyphCanvas` imported from `../generate_samples.py`, including its original TeleSys font rendering and Qud palette. It does not use image generation or resampled glyph textures.

- Final asset: `space/assets/img/objects/space_station2.png`, 384×384 RGBA, binary transparency.
- Grid: 48 columns × 24 rows, native 8×16 character cells.
- All visible artwork is actual printable ASCII glyphs and per-cell backgrounds.
- Main dome: rounded stepped profile, longitude ribs, shaded characters, colonnaded drum.
- Docking bay: in the smaller south dome, amber brackets around a dark mouth, approximate center (192,320). The approach below remains transparent.
- `station.txt` preserves the literal character grid; `station.cells.json` preserves each cell's glyph and colors.
- `validation.json` confirms that every rendered cell matches its TeleSys glyph mask and assigned colors.

Regenerate with `python tools/art/qud_glyph/capitol/generate_station.py` from the repository root. The script and its glyph source stay in `tools/art/` (outside the game tree). It writes the station PNG into `space/assets/img/objects/`, which is what the game loads.
