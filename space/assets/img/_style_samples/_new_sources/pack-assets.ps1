param([string]$Manifest = (Join-Path $PSScriptRoot 'sources.json'))
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Drawing
Add-Type -ReferencedAssemblies System.Drawing.Common,System.Drawing.Primitives,System.Private.Windows.GdiPlus,System.Private.Windows.Core,System.Collections -TypeDefinition @'
using System;
using System.Drawing;
using System.Drawing.Imaging;
using System.Collections.Generic;
public static class SampleAssetPacker {
  static Color[] palette;
  static Dictionary<int,Color> cache = new Dictionary<int,Color>();
  public static void Palette(string[] hex) {
    palette=Array.ConvertAll(hex,s=>ColorTranslator.FromHtml(s)); cache.Clear();
  }
  static Color Read(Bitmap src, int x, int y) {
    if (x < 0 || y < 0 || x >= src.Width || y >= src.Height) return Color.Transparent;
    Color c = src.GetPixel(x,y);
    if(c.A<128) return Color.FromArgb(0,0,0,0);
    int key=c.ToArgb() & 0xffffff;
    if(cache.TryGetValue(key,out var known)) return known;
    double best=double.MaxValue; Color match=palette[0];
    foreach(Color p in palette) {
      double dr=c.R-p.R,dg=c.G-p.G,db=c.B-p.B;
      double distance=2*dr*dr+4*dg*dg+3*db*db;
      if(distance<best) { best=distance; match=p; }
    }
    cache[key]=match; return match;
  }
  static Rectangle Bounds(Bitmap src, int left, int right) {
    int x0=right, x1=left, y0=src.Height, y1=0;
    for(int y=0;y<src.Height;y++) for(int x=left;x<right;x++) {
      if(src.GetPixel(x,y).A<128) continue;
      x0=Math.Min(x0,x); x1=Math.Max(x1,x); y0=Math.Min(y0,y); y1=Math.Max(y1,y);
    }
    return Rectangle.FromLTRB(x0,y0,x1+1,y1+1);
  }
  public static void Square(string source, string target, int size) {
    using(var src=new Bitmap(source)) using(var dst=new Bitmap(size,size,PixelFormat.Format32bppArgb)) {
      Rectangle b=Bounds(src,0,src.Width);
      int margin=size==576?12:12;
      double scale=(double)Math.Max(b.Width,b.Height)/(size-2*margin);
      for(int y=margin;y<size-margin;y++) for(int x=margin;x<size-margin;x++)
        dst.SetPixel(x,y,Read(src,(int)Math.Floor(b.Left+b.Width/2.0+(x+.5-size/2.0)*scale),(int)Math.Floor(b.Top+b.Height/2.0+(y+.5-size/2.0)*scale)));
      dst.Save(target,ImageFormat.Png);
    }
  }
  public static void Ship(string source, string target, int hullBottom) {
    using(var src=new Bitmap(source)) using(var dst=new Bitmap(288,48,PixelFormat.Format32bppArgb)) {
      var bounds=new Rectangle[6];
      for(int f=0;f<6;f++) bounds[f]=Bounds(src,src.Width*f/6,src.Width*(f+1)/6);
      // One stable generated hull, six generated exhaust phases. Preserve proportions.
      double scale=(hullBottom-bounds[0].Top)/32.0;
      for(int f=0;f<6;f++) for(int y=0;y<48;y++) for(int x=0;x<48;x++) {
        int sourceFrame=y<36?0:f;
        Rectangle b=bounds[sourceFrame];
        int sx=(int)Math.Floor(b.Left+b.Width/2.0+(x+.5-24)*scale);
        int sy=(int)Math.Floor(b.Top+(y+.5-4)*scale);
        if(sx<src.Width*sourceFrame/6 || sx>=src.Width*(sourceFrame+1)/6) continue;
        dst.SetPixel(f*48+x,y,Read(src,sx,sy));
      }
      dst.Save(target,ImageFormat.Png);
    }
  }
}
'@
$assetRoot = Split-Path $PSScriptRoot -Parent
$palettes = Get-Content -LiteralPath (Join-Path $PSScriptRoot 'palettes.json') -Raw | ConvertFrom-Json -AsHashtable
foreach ($asset in (Get-Content -LiteralPath $Manifest -Raw | ConvertFrom-Json)) {
  [SampleAssetPacker]::Palette([string[]]$palettes[$asset.direction])
  $target = Join-Path $assetRoot ($asset.direction + '/' + $asset.output)
  New-Item -ItemType Directory -Force -Path (Split-Path $target -Parent) | Out-Null
  if ($asset.type -eq 'ship') {
    [SampleAssetPacker]::Ship($asset.source, $target, $asset.hullBottom)
  } else {
    [SampleAssetPacker]::Square($asset.source, $target, $asset.size)
  }
  Write-Output $target
}
