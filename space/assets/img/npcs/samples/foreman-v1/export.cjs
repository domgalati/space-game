// Mechanical export of generated concepts; does not draw character artwork.
// Usage: node export.cjs <sharp-module-path> <human-source> <vessari-source> <muroth-source>
const fs = require('node:fs');
const path = require('node:path');
const sharp = require(process.argv[2]);
const root = __dirname;
const species = ['human', 'vessari', 'muroth'];
const widths = [12, 10, 16];
const palettes = [
  ['161e30','424e63','949da7','e0dfd9','c39837','dba36d','60412b','aa714b'],
  ['161e30','424e63','738a9d','e0dfd9','c39837','94b1bd','287c89','b9e1df'],
  ['161e30','424e63','949da7','e0dfd9','c39837','a97839','523f29','d9ab5a'],
].map(p=>p.map(c=>Buffer.from(c,'hex')));
const report = [];

async function main() {
  fs.mkdirSync(path.join(root, 'sources'), {recursive:true});
  for (let s = 0; s < species.length; s++) {
    const source = process.argv[s+3];
    const retainedSource=path.join(root, 'sources', `${species[s]}-generated.png`);
    if(path.resolve(source)!==path.resolve(retainedSource)) fs.copyFileSync(source,retainedSource);
    const {data, info} = await sharp(source).ensureAlpha().raw().toBuffer({resolveWithObject:true});
    let left=info.width, top=info.height, right=0, bottom=0;
    for(let y=0;y<info.height;y++) for(let x=0;x<info.width;x++) {
      if(data[(y*info.width+x)*4+3] >= 128) {
        left=Math.min(left,x); top=Math.min(top,y); right=Math.max(right,x); bottom=Math.max(bottom,y);
      }
    }
    const crop={left,top,width:right-left+1,height:bottom-top+1};
    const resized=await sharp(source).extract(crop).resize(widths[s],22,{fit:'fill',kernel:'nearest'}).ensureAlpha().raw().toBuffer();
    for(let i=0;i<resized.length;i+=4) {
      resized[i+3]=resized[i+3]>=128?255:0;
      if(!resized[i+3]) resized.fill(0,i,i+3);
    }
    const pixels=resized;
    const canvas=Buffer.alloc(24*24*4);
    const offset=Math.floor((24-widths[s])/2);
    const colors=new Set();
    for(let y=0;y<22;y++) for(let x=0;x<widths[s];x++) {
      const i=(y*widths[s]+x)*4, out=((y+1)*24+x+offset)*4;
      if(pixels[i+3]>=128) {
        const closest=palettes[s].reduce((best,c)=>{
          const dist=c.reduce((sum,v,k)=>sum+(v-pixels[i+k])**2,0);
          return dist<best.dist?{color:c,dist}:best;
        },{color:null,dist:Infinity}).color;
        closest.copy(canvas,out); canvas[out+3]=255;
        colors.add(canvas.subarray(out,out+3).toString('hex'));
      }
    }
    if(colors.size>8) throw new Error(`Too many opaque colors: ${colors.size}`);
    const filename=`${species[s]}-foreman-v1.png`;
    await sharp(canvas,{raw:{width:24,height:24,channels:4}}).png().toFile(path.join(root,filename));
    report.push({species:species[s],file:filename,width:24,height:24,format:'PNG',mode:'RGBA',opaque_colors:colors.size,alpha_values:[0,255],source_crop:crop,export_width:widths[s],export_height:22});
  }
  const labels=['Existing Foreman','A - Human','B - Vessari','C - Muroth'];
  const files=[path.resolve(root,'../../../objects/foreman.png'),...species.map(s=>path.join(root,`${s}-foreman-v1.png`))];
  const caption=`<svg width="900" height="350"><rect width="900" height="350" fill="#19212e"/><g fill="#e4e7ed" font-family="sans-serif"><text x="24" y="28" font-size="18">FOREMAN / SPECIES APPROVAL SAMPLES</text>${labels.map((label,i)=>`<text x="${i*220+24}" y="62" font-size="15">${label}</text>`).join('')}<text x="24" y="337" font-size="12">Top: 8x nearest-neighbor preview. Below: actual 24x24 assets. Transparent PNGs; samples are not installed.</text></g></svg>`;
  const layers=[];
  for(let i=0;i<files.length;i++) {
    layers.push({input:await sharp(files[i]).resize(192,192,{kernel:'nearest'}).png().toBuffer(),left:i*220+24,top:80});
    layers.push({input:files[i],left:i*220+108,top:287});
  }
  await sharp(Buffer.from(caption)).composite(layers).png().toFile(path.join(root,'approval-sheet.png'));
  fs.writeFileSync(path.join(root,'validation.json'),JSON.stringify(report,null,2)+'\n');
  console.log(JSON.stringify(report,null,2));
}
main().catch(e=>{console.error(e);process.exit(1)});
