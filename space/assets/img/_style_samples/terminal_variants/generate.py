"""Deterministic terminal bezel art. Does not change or import game code.

The original screen's connected black pixel region is protected verbatim.
All lettering and surface glyphs use the game's native 8x16 TeleSys cells.
"""
from collections import deque
import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
IMG = ROOT.parents[1]
SOURCE = IMG / "objects" / "terminal_screen.png"
FONT = IMG.parent / "fonts" / "TeleSys.ttf"
font = ImageFont.truetype(str(FONT), 16)

PALETTES = {
    "ship": dict(dark="#06100f", recess="#0b1a19", shadow="#10292c", face="#173c40",
                 mid="#28595b", edge="#50817b", light="#b1c9c3", white="#e2ecda",
                 accent="#77bfcf", dim="#155352", signal="#99dd99", warning="#cfc041"),
    "market": dict(dark="#16140c", recess="#242314", shadow="#343921", face="#484c2c",
                   mid="#666544", edge="#98875f", light="#c7bb8b", white="#eee4ba",
                   accent="#d7b75b", dim="#65603c", signal="#99ba80", warning="#c68a48"),
    "docking": dict(dark="#10171c", recess="#19232b", shadow="#24343c", face="#344650",
                    mid="#4d6469", edge="#738d8b", light="#b1c9c3", white="#e2e4cb",
                    accent="#e99f10", dim="#445c62", signal="#99bb99", warning="#a64a2e"),
}


def screen_mask(src):
    data=np.array(src)
    seen=np.zeros(data.shape[:2],dtype=bool)
    q=deque([(260,440)])
    seen[260,440]=True
    target=data[260,440]
    while q:
        y,x=q.popleft()
        for yy,xx in ((y-1,x),(y+1,x),(y,x-1),(y,x+1)):
            if 0<=xx<880 and 0<=yy<520 and not seen[yy,xx] and np.array_equal(data[yy,xx],target):
                seen[yy,xx]=True
                q.append((yy,xx))
    return seen


class Bezel:
    def __init__(self,kind,src,mask):
        self.kind=kind
        self.p=PALETTES[kind]
        self.src=src
        self.mask=mask
        self.im=Image.new("RGBA",src.size,(0,0,0,255))
        self.draw=ImageDraw.Draw(self.im)
        self.cells=[]

    def rect(self,box,color):
        self.draw.rectangle(box,fill=self.p.get(color,color))

    def line(self,points,color,width=1):
        self.draw.line(points,fill=self.p.get(color,color),width=width)

    def panel(self,box,color="face",chamfer=6):
        x0,y0,x1,y1=box
        c=chamfer
        pts=[(x0+c,y0),(x1-c,y0),(x1,y0+c),(x1,y1-c),
             (x1-c,y1),(x0+c,y1),(x0,y1-c),(x0,y0+c)]
        self.draw.polygon(pts,fill=self.p[color])
        self.line(pts[:3],"edge",2)
        self.line(pts[3:7],"dark",2)
        self.line([pts[7],pts[0]],"edge",2)

    def text(self,x,y,text,color="light",scale=1):
        # Literal glyph masks: no antialiasing or resampling except integer nearest.
        for index,ch in enumerate(text):
            assert 32<=ord(ch)<=126
            tile=Image.new("1",(8,16),0)
            d=ImageDraw.Draw(tile)
            d.fontmode="1"
            d.text((0,0),ch,font=font,fill=1)
            if scale!=1:
                tile=tile.resize((8*scale,16*scale),Image.Resampling.NEAREST)
            px=x+index*8*scale
            self.im.paste(self.p[color],(px,y),tile)
            self.cells.append(dict(x=px,y=y,glyph=ch,color=self.p[color],scale=scale))

    def screw(self,x,y):
        self.rect((x-4,y-3,x+4,y+3),"dark")
        self.rect((x-3,y-4,x+3,y+4),"dark")
        self.rect((x-3,y-2,x+2,y+2),"edge")
        self.line([(x-2,y),(x+2,y)],"recess")

    def glyph_panel(self,x,y,lines,color="dim"):
        for row,line in enumerate(lines):
            self.text(x,y+row*16,line,color)

    def keys(self,labels):
        for i,ch in enumerate(labels):
            x=704+i*32
            self.panel((x,458,x+25,488),"dark",3)
            self.rect((x+3,461,x+21,482),"mid")
            self.line([(x+3,461),(x+21,461),(x+21,479)],"light")
            self.text(x+8,464,ch,"white")

    def base(self):
        # Shared shell footprint; opening is carved from the exact source pixel mask.
        self.panel((16,12,860,505),"shadow",20)
        self.panel((24,18,852,497),"face",16)
        self.line([(40,18),(836,18),(850,32)],"light",2)
        self.line([(26,39),(26,479),(41,494)],"mid",3)
        self.line([(851,38),(851,480),(837,496),(44,496)],"dark",4)
        self.panel((38,28,837,74),"recess",6)
        self.line([(104,28),(805,28)],"edge")
        self.line([(104,72),(805,72)],"dark",2)

        # Thin character rails bind the NES shell to the terminal character language.
        self.text(104,16,"+"+"="*86+"+","dim")
        self.text(104,416,"+"+"-"*86+"+","edge")
        for y in range(112,401,16):
            self.text(64,y,":" if (y//16)%3 else "|","edge")
            self.text(800,y,":" if (y//16)%3 else "|","dim")

        # Exact rounded glass geometry, expressed as stepped pixel-distance bands.
        yy,xx=np.indices(self.mask.shape)
        dilations=[]
        for radius in (12,8,4,2):
            grown=np.zeros_like(self.mask)
            for dy in range(-radius,radius+1):
                for dx in range(-radius,radius+1):
                    if dx*dx+dy*dy>radius*radius:
                        continue
                    y0,y1=max(0,dy),min(520,520+dy)
                    x0,x1=max(0,dx),min(880,880+dx)
                    grown[y0:y1,x0:x1]|=self.mask[y0-dy:y1-dy,x0-dx:x1-dx]
            dilations.append(grown)
        pixels=np.array(self.im)
        for grown,color in zip(dilations,("dark","mid","recess","dark")):
            pixels[grown]=(*ImageColorRGB(self.p[color]),255)
        # A restrained upper-left glint; still no pixels enter the protected screen.
        rim=dilations[1] & ~dilations[2] & ((yy<95)|(xx<87))
        pixels[rim]=(*ImageColorRGB(self.p["edge"]),255)
        pixels[self.mask]=np.array(self.src)[self.mask]
        self.im=Image.fromarray(pixels)
        self.draw=ImageDraw.Draw(self.im)
        for x,y in ((40,34),(835,34),(40,483),(835,483)):
            self.screw(x,y)

    def ship(self):
        self.text(112,32,"SHIP TERMINAL","white",2)
        self.glyph_panel(592,32,["+-- NAV / COMMS --+","| : . + . : . : |"],"accent")
        self.glyph_panel(56,32,[" /\\ ","<||>"," \\/ "],"accent")
        # Narrow repeated ASCII ribs on the outside rails.
        for x in (32,816):
            for y in (112,208,304):
                self.panel((x-3,y-4,x+25,y+62),"recess",4)
                self.glyph_panel(x,y,["+-+","|:|","|:|","+-+"],"dim")
                self.text(x+8,y+16,"=","accent")
        self.panel((48,437,232,489),"recess",5)
        self.glyph_panel(64,440,[".---+---.   . : .", "| . | . | --+--*", "'---+---'   : . :"],"edge")
        self.text(104,456,"*","accent")
        self.panel((248,437,682,489),"shadow",6)
        self.text(264,440,"NAVIGATION / COMMUNICATIONS / SYSTEMS","light")
        self.text(264,464,"[::]--+--[::]--+--[::]--+--[::]","dim")
        self.line([(266,484),(652,484)],"mid",2)
        for x in range(272,656,16):
            self.rect((x,483,x+2,487),"edge")
        self.keys("+*:=")

    def market(self):
        self.text(112,32,"MARKET TERMINAL","white",2)
        self.glyph_panel(616,32,["+-- EXCHANGE --+","|::|::|::|::|::|"],"accent")
        self.glyph_panel(56,32,["/==\\","|$$|","\\==/"],"accent")
        # Brass register side plates with literal ledger ticks and engraved columns.
        for x in (32,816):
            self.panel((x-3,100,x+25,402),"recess",4)
            for y in range(112,385,16):
                self.text(x,y,"|=|" if y%48==16 else "|:|","dim")
            for y in (128,240,352):
                self.text(x+8,y,"$","accent")
        # A recessed paper/ledger cassette rendered as ASCII, not fake screen text.
        self.panel((48,437,240,490),"recess",5)
        self.glyph_panel(64,440,["+----+----+----+----+","|::::|::::|::::|::::|","+====+====+====+====+"],"edge")
        self.panel((256,437,682,489),"shadow",6)
        self.text(272,440,"TRADE / LEDGER / CARGO","light")
        self.text(272,464,"[$] :: [#] :: [=] :: [$] :: [#]","accent")
        for x in range(268,661,8):
            self.rect((x,486,x+1,487),"edge")
        self.keys("$#=+")
        for x in (52,792):
            self.line([(x,84),(x,414)],"mid",2)
            self.line([(x+3,84),(x+3,414)],"dark")

    def docking(self):
        self.text(112,32,"DOCKING TERMINAL","white",2)
        self.glyph_panel(640,32,["+-- PORT --+","|[ ] <> [ ]|"],"accent")
        self.glyph_panel(56,32,["[||]",">  <","[__]"],"accent")
        # Mechanical clamps plus ASCII caution bands; muted surfaces, amber marks.
        for x in (28,812):
            for y in (112,304):
                self.panel((x-3,y-10,x+33,y+87),"mid",6)
                self.rect((x+2,y-5,x+28,y+4),"accent")
                self.rect((x+2,y+68,x+28,y+77),"accent")
                self.glyph_panel(x+4,y+8,["[|]","[|]","[|]"],"dark")
                self.text(x+4,y+56,"///","warning")
        self.panel((48,437,248,490),"recess",4)
        self.glyph_panel(64,440,["+---+         +---+","| : | >  <  > | : |","+---+         +---+"],"edge")
        self.text(112,456,">  <","accent")
        self.panel((264,437,682,489),"shadow",5)
        self.text(280,440,"APPROACH / BERTH / DEPART","light")
        self.text(280,464,"////  [|]---[  ]---[|]  ////","accent")
        self.keys("[]<>")
        for x in (80,752):
            self.text(x,80,"/////","accent")
            self.text(x,400,"/////","dim")

    def finish(self):
        self.base()
        getattr(self,self.kind)()
        pixels=np.array(self.im)
        # Pixel lock applied after every decoration, guaranteeing zero encroachment.
        pixels[self.mask]=np.array(self.src)[self.mask]
        self.im=Image.fromarray(pixels)
        return self.im


def ImageColorRGB(value):
    return tuple(int(value[i:i+2],16) for i in (1,3,5))


def main():
    source=Image.open(SOURCE).convert("RGBA")
    assert source.size==(880,520)
    mask=screen_mask(source)
    ys,xs=np.where(mask)
    assert (xs.min(),ys.min(),xs.max(),ys.max())==(91,88,782,408)
    original=np.array(source)
    records=[]
    for kind in PALETTES:
        bezel=Bezel(kind,source,mask)
        result=bezel.finish()
        data=np.array(result)
        assert np.array_equal(data[mask],original[mask])
        assert np.array_equal(data[:,:,3],original[:,:,3])
        # Same exact screen boundary, not just black pixels copied into a larger hole.
        assert np.array_equal(screen_mask(result),mask)
        target=ROOT/kind/"terminal_screen.png"
        target.parent.mkdir(parents=True,exist_ok=True)
        result.save(target)
        (ROOT/kind/"glyphs.json").write_text(json.dumps(bezel.cells,indent=2)+"\n",encoding="utf-8")
        records.append(dict(file=f"{kind}/terminal_screen.png",size=list(result.size),mode=result.mode,
                            colors=len(np.unique(data.reshape(-1,4),axis=0)),
                            glyph_count=len(bezel.cells),screen_pixels_unchanged=True,
                            screen_boundary_unchanged=True,alpha_channel_unchanged=True,
                            sha256=hashlib.sha256(target.read_bytes()).hexdigest()))
    report=dict(source=str(SOURCE),source_sha256=hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
                screen_bounds_xyxy_exclusive=[91,88,783,409],screen_pixel_count=int(mask.sum()),
                font=str(FONT),font_size=16,native_glyph_cell=[8,16],antialiasing=False,
                outputs=records)
    (ROOT/"validation.json").write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(report,indent=2))


if __name__=="__main__":
    main()
