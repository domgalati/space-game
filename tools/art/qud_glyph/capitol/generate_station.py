"""Capitol station drawn entirely with the existing 8x16 TeleSys GlyphCanvas.

Run with the same numpy/Pillow environment as ../generate_samples.py.
Only writes this revision's station, cell data, text source, and validation.
"""
from pathlib import Path
import importlib.util
import json
import math

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[4]
spec = importlib.util.spec_from_file_location("sample_art", ROOT.parent / "generate_samples.py")
art = importlib.util.module_from_spec(spec)
spec.loader.exec_module(art)
canvas = art.GlyphCanvas(48, 24)
Q = art.QUD
HULL = art.QUD_BG["hull"]
DEEP = art.QUD_BG["deep"]


def put(x, y, char, color="y", bg=None):
    assert len(char) == 1 and 32 <= ord(char) <= 126
    canvas.set(x, y, char, Q[color], bg)


def run(x, y, chars, color="y", bg=HULL):
    for i, char in enumerate(chars):
        put(x + i, y, char, color, bg)


def centered(y, chars, color="y", bg=HULL, shaded=False):
    x = (48 - len(chars)) // 2
    for i, char in enumerate(chars):
        tone = color
        if shaded and char != " ":
            t = i / max(1, len(chars) - 1)
            tone = "Y" if t < .26 else "y" if t < .55 else "C" if t < .78 else "K"
        put(x+i, y, char, tone, bg)


# The orbital ring is a band of actual characters, with transparent open space.
# Rear half is quiet; near half is brighter. Grid aspect ratio is already 8:16.
for x in range(2, 46):
    nx = (x - 23.5) / 21.5
    dy = 5.0 * math.sqrt(max(0, 1-nx*nx))
    for front in (False, True):
        y = round(11.5 + (dy if front else -dy))
        steep = abs(nx) > .86
        char = "|" if steep else "="
        if .6 < abs(nx) <= .86:
            char = ("\\" if nx < 0 else "/") if front else ("/" if nx < 0 else "\\")
        if x % 6 == 0:
            char = "+"
        put(x, y, char, "C" if front else "K", DEEP)
        if not steep:
            put(x, y+(1 if front else -1), "." if not front else ":", "k")

# Exposed ring struts at the sides of the rotunda.
for x, y, ch in [(7,9,"\\"),(8,10,"\\"),(9,11,"\\"),
                 (40,9,"/"),(39,10,"/"),(38,11,"/"),
                 (7,15,"/"),(8,14,"/"),(40,15,"\\"),(39,14,"\\")]:
    put(x,y,ch,"c",DEEP)

# Small communication masts, discrete green lamps.
for x in (9,38):
    put(x,4,"*","G")
    put(x,5,"|","C")
    put(x,6,"|","K")
    run(x-1,7,"/|\\","c",None)

# Capitol wings: pitched roof, repeated columns, recessed windows, cornices.
for start in (5,31):
    run(start+2,10,".------.","K")
    run(start+1,11,"/========\\","y")
    run(start,12,"+----------+","C")
    run(start,13,"|H H H H H |","y")
    run(start,14,"||:|:|:|:|:|","c")
    run(start,15,"+==========+","y")
    run(start+1,16,"'--:--:--'","K")

# Lantern and statue. No filled block characters: all shading is character choice.
centered(1,"*","G",None)
centered(2,"/\\","y",None)
centered(3,"[||]","y")
centered(4,".====.","Y")

# A hemispherical profile: rapid widening at the crown, vertical at the rim.
# Dome longitude ribs curve outward rather than making a triangular roof.
for y, width in enumerate((12,18,22,24,24,24), start=5):
    chars=[]
    for i in range(width):
        if i==0:
            ch="." if y==5 else "/" if y<8 else "("
        elif i==width-1:
            ch="." if y==5 else "\\" if y<8 else ")"
        elif y==10:
            ch="=" if i%3 else "|"
        elif i%2==0:
            ch="/" if y<7 and i<width//2 else "\\" if y<7 else "|"
        else:
            ch="#" if i<width//3 and y>=7 else ":" if i<width*2//3 else "."
        chars.append(ch)
    centered(y,"".join(chars),shaded=True)
centered(11,"+========================+","y")

# Cylindrical colonnade under the dome, broad plinth beneath.
centered(12,"|H H H H H H H H H H H H |",shaded=True)
centered(13,"||:|:|:|:|:|:|:|:|:|:|:|:|",shaded=True)
centered(14,"\\========================/","C")
centered(15,"'--::--::--::--::--'","K")

# SOUTH dome projects from the drum. Its face houses the actual docking mouth.
centered(16,".------.","y")
centered(17,"./|:|:|:|\\.",shaded=True)
centered(18,"/==|=|=|=|==\\","C")
centered(19,"[|        |]","O",art.QUD_BG["void"])
centered(20,"[|_      _|]","W",art.QUD_BG["void"])
put(16,19,"*","G")
put(31,19,"*","G")

# Underside service stacks flank an empty southern approach, never cross the bay.
for x, end in ((9,19),(12,21),(15,22),(32,22),(35,21),(38,19)):
    for y in range(17,end+1):
        put(x,y,"|" if y==17 else ":" if y<end else ".","c" if y==17 else "K")


def main():
    pixels = canvas.render()
    target = REPO / "space" / "assets" / "img" / "objects" / "space_station2.png"
    target.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(pixels).save(target)
    # Keep the literal character layout and every foreground/background assignment.
    lines = ["".join(canvas.cells.get((x,y),(" ",None,None))[0] for x in range(48))
             for y in range(24)]
    (ROOT / "station.txt").write_text("\n".join(lines)+"\n", encoding="utf-8")
    cells = [{"column":x,"row":y,"glyph":ch,"foreground":fg,"background":bg}
             for (x,y),(ch,fg,bg) in sorted(canvas.cells.items(), key=lambda item:(item[0][1],item[0][0]))]
    (ROOT / "station.cells.json").write_text(json.dumps(cells,indent=2)+"\n",encoding="utf-8")
    # Verify every 8x16 tile matches its literal glyph and declared background.
    for (x,y),(ch,fg,bg) in canvas.cells.items():
        tile=pixels[y*16:(y+1)*16,x*8:(x+1)*8]
        expected=np.zeros((16,8,4),dtype=np.uint8)
        if bg is not None:
            expected[:,:,:3]=art.hex_rgb(bg)
            expected[:,:,3]=255
        if ch != " ":
            mask=canvas.glyph(ch)
            expected[mask,:3]=art.hex_rgb(fg)
            expected[mask,3]=255
        assert np.array_equal(tile,expected),(x,y,ch)
    assert pixels.shape==(384,384,4)
    assert set(np.unique(pixels[:,:,3]))=={0,255}
    assert not np.any(pixels[-48:,18*8:30*8,3]), "South approach must stay open"
    report={"size":[384,384],"mode":"RGBA","cell_size":[8,16],"grid":[48,24],
            "font":"TeleSys.ttf at 16px","literal_ascii_only":True,
            "cell_count":len(cells),"every_cell_matches_font_mask":True,
            "alpha_values":[0,255],"south_approach_clear":True,
            "bay_center":[192,320]}
    (ROOT/"validation.json").write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(report))


if __name__=="__main__":
    main()
