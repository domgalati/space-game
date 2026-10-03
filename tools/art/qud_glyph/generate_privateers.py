"""Privateer ships: three classes in each raider faction's colours, built like the barge.

Each sheet is 288x48: six 48x48 north-facing frames with flickering engines, on the same
6x6 grid of 8x8 glyph stamps as the live barge, so the game rotates them the same way.

Run from the repository root: python tools/art/qud_glyph/generate_privateers.py
Writes space/assets/img/ships/privateer_<class>_<faction>.png.
"""
from pathlib import Path
import importlib.util

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[2]
spec = importlib.util.spec_from_file_location("sample_art", ROOT / "generate_samples.py")
art = importlib.util.module_from_spec(spec)
spec.loader.exec_module(art)

OUT = REPO / "space" / "assets" / "img" / "ships"
FRAME, FRAMES, CELL = 48, 6, 8

# Extra stamps for sharper hulls: filled half-peaks and wing triangles.
EXTRA = {
    "p": ["".join("1" if x >= 7 - y else "0" for x in range(8)) for y in range(8)],  # lower-right fill
    "q": ["".join("1" if x <= y else "0" for x in range(8)) for y in range(8)],  # lower-left fill
    "b": ["".join("1" if x >= y else "0" for x in range(8)) for y in range(8)],  # upper-right fill
    "d": ["".join("1" if x <= 7 - y else "0" for x in range(8)) for y in range(8)],  # upper-left fill
    "=": ["00000000", "11111111", "11111111", "00000000", "00000000", "11111111", "11111111", "00000000"],
    "o": ["00111100", "01111110", "11100111", "11000011", "11000011", "11100111", "01111110", "00111100"],
}

# Layout, colour role and background per cell. Roles: m main, l light, k dark, w window, f flame.
# Flame cells (role f) cycle through the barge's flame glyphs.
CLASSES = {
    # Fast and fragile: a narrow dart with swept wings.
    "cutter": (
        ["..^^..", "..nn..", ".pDDq.", "pD[]Dq", "D.LL.D", "..ff.."],
        ["..ll..", "..ww..", ".lmml.", "lmkkml", "m.mm.m", "..ff.."],
        ["......", "..hh..", "..hh..", ".hhhh.", "..hh..", "......"],
    ),
    # Balanced: twin forward prongs over a broad body.
    "raider": (
        [".^..^.", ".D..D.", "pD++Dq", "D[nn]D", "DLLLLD", ".f..f."],
        [".l..l.", ".m..m.", "lmkkml", "mkwwkm", "mmmmmm", ".f..f."],
        ["......", ".h..h.", ".hhhh.", "hhhhhh", "hhhhhh", "......"],
    ),
    # Slow and heavy: a slab with a turret and four engines.
    "gunship": (
        [".+==+.", "DD[]DD", "D[oo]D", "DLLLLD", "bD==Dd", "f.ff.f"],
        [".lkkl.", "mmkkmm", "mkwwkm", "mmmmmm", "lmkkml", "f.ff.f"],
        ["..hh..", "hhhhhh", "hhhhhh", "hhhhhh", ".hhhh.", "......"],
    ),
}

# Light, main, dark, background. Main is the faction colour from the portrait palette.
FACTIONS = {
    "dominion": ("#e07882", "#b3424e", "#5c1f26", "#1e0b0e"),
    "cohort": ("#8fd3a0", "#5bae70", "#2a5a36", "#0a1a0f"),
    "caravaneers": ("#eba06e", "#cc733f", "#6b3a1e", "#1e1109"),
}
WINDOW = "#cfc041"
FLAMES = [".", "'", '"', "!", '"', "'"]
FLAME_COLOURS = ["o", "o", "O", "Y", "O", "o"]


def stamp(name):
    rows = EXTRA.get(name) or art._GLYPH8[name]
    return np.array([[ch == "1" for ch in row] for row in rows])


def frame(layout, roles, backgrounds, palette, index):
    light, main, dark, bg = palette
    colours = {"l": light, "m": main, "k": dark, "w": WINDOW}
    out = np.zeros((FRAME, FRAME, 4), dtype=np.uint8)
    for row in range(6):
        for col in range(6):
            char, role = layout[row][col], roles[row][col]
            if char == ".":
                continue
            block = out[row * CELL:(row + 1) * CELL, col * CELL:(col + 1) * CELL]
            if backgrounds[row][col] == "h":
                block[..., :3] = art.hex_rgb(bg)
                block[..., 3] = 255
            if role == "f":
                char, colour = FLAMES[index], art.QUD[FLAME_COLOURS[index]]
            else:
                colour = colours[role]
            ink = stamp(char)
            block[ink, :3] = art.hex_rgb(colour)
            block[ink, 3] = 255
    return out


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for kind, (layout, roles, backgrounds) in CLASSES.items():
        for faction, palette in FACTIONS.items():
            sheet = np.zeros((FRAME, FRAME * FRAMES, 4), dtype=np.uint8)
            for i in range(FRAMES):
                sheet[:, i * FRAME:(i + 1) * FRAME] = frame(layout, roles, backgrounds, palette, i)
            path = OUT / f"privateer_{kind}_{faction}.png"
            Image.fromarray(sheet, "RGBA").save(path)
            print("wrote", path.relative_to(REPO))


if __name__ == "__main__":
    main()
