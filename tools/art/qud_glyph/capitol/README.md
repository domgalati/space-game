# Capitol station — literal glyph revision

This revision uses `GlyphCanvas` imported from `../generate_samples.py`, including its original TeleSys font rendering and Qud palette. It does not use image generation or resampled glyph textures.

- Final asset: `space/assets/img/objects/space_station2.png`, 2304×2304 RGBA (the size of a flight planet), binary transparency.
- Grid: 288 columns × 144 rows, native 8×16 character cells, so glyphs match the planets and ship computers at 1:1.
- All visible artwork is actual printable ASCII glyphs and per-cell backgrounds.
- Shapes are computed per cell and lit from the upper left like the planet disks: the main dome is a sphere with meridian ribs and latitude bands, the colonnade a cylinder, the habitat ring a deck ellipse with an outer wall on its near half.
- Main dome: ribbed hemisphere on an attic of round windows, lantern with statue and green lamp, glass colonnaded drum. Wings are lower pedimented annexes; masts stand on the ring.
- Docking bay: in the smaller south dome, amber brackets and hazard lintel around a dark hangar, center (1152,1920). `sol.json` uses that as Nexum Astra's access point. The approach below remains transparent.
- `station.txt` preserves the literal character grid. Colors live in the generator.
- `validation.json` confirms that every rendered cell matches its TeleSys glyph mask and assigned colors.

Regenerate with `python tools/art/qud_glyph/capitol/generate_station.py` from the repository root. The script and its glyph source stay in `tools/art/` (outside the game tree). It writes the station PNG into `space/assets/img/objects/`, which is what the game loads.
