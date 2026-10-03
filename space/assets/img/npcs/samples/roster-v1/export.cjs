// Mechanical production-format export; character artwork comes from image_gen.
// node export.cjs <sharp-module-path>
const fs=require('node:fs');
const path=require('node:path');
const crypto=require('node:crypto');
const sharp=require(process.argv[2]);
const root=__dirname;
const {assets}=require('./generation.json');
const sourceFiles=require('./source-files.json');
const jobColors={miner:'a94632',dockworker:'527047',security:'426493',politician:'592650'};
const prefixes={miner:'M',dockworker:'D',security:'S',politician:'P'};
const species=['human','vessari','muroth'];
const names=['Human','Vessari','Muroth'];
const reviewId=a=>a.id==='hesk-durran'?'H1':prefixes[a.job]+(species.indexOf(a.species)+1);
const report=[];

function paletteFor(a){
  if(a.id==='hesk-durran') return ['161e30','424e63','949da7','e0dfd9','c39837','b98137','523f29','76c6d7'];
  const skin={human:['dba36d','aa714b'],vessari:['94b1bd','287c89'],muroth:['d9ab5a','523f29']}[a.species];
  return ['161e30','424e63','949da7','e0dfd9','c39837',...skin,jobColors[a.job]];
}

async function exportAsset(a){
  if(!sourceFiles[a.id]) throw new Error('Missing source for '+a.id);
  const source=path.resolve(root,sourceFiles[a.id]);
  const retained=path.join(root,'sources',a.id+'.png');
  if(path.resolve(source)!==path.resolve(retained))fs.copyFileSync(source,retained);
  const {data,info}=await sharp(source).ensureAlpha().raw().toBuffer({resolveWithObject:true});
  let left=info.width,top=info.height,right=-1,bottom=-1;
  for(let y=0;y<info.height;y++)for(let x=0;x<info.width;x++){
    if(data[(y*info.width+x)*4+3]>=128){left=Math.min(left,x);right=Math.max(right,x);top=Math.min(top,y);bottom=Math.max(bottom,y);}
  }
  if(right<left)throw new Error('Empty image '+a.id);
  const crop={left,top,width:right-left+1,height:bottom-top+1};
  const width=a.id==='miner-human'?16:({human:12,vessari:10,muroth:16}[a.species])+(a.job==='miner'?2:0);
  const small=await sharp(source).extract(crop).resize(width,22,{fit:'fill',kernel:'nearest'}).ensureAlpha().raw().toBuffer();
  // Center the sampling grid for this source to retain both one-pixel eyes.
  if(a.id==='miner-human')for(let y=0;y<22;y++)for(let x=0;x<width;x++){
    const sx=left+Math.floor((x+0.5)*crop.width/width);
    const sy=top+Math.floor((y+0.5)*crop.height/22);
    data.copy(small,(y*width+x)*4,(sy*info.width+sx)*4,(sy*info.width+sx)*4+4);
  }
  const colors=paletteFor(a).map(v=>Buffer.from(v,'hex'));
  const canvas=Buffer.alloc(24*24*4),offset=Math.floor((24-width)/2);
  for(let y=0;y<22;y++)for(let x=0;x<width;x++){
    const i=(y*width+x)*4;
    if(small[i+3]<128)continue;
    const color=colors.reduce((best,c)=>{
      const d=c.reduce((sum,v,k)=>sum+(v-small[i+k])**2,0);
      return d<best.d?{c,d}:best;
    },{c:null,d:Infinity}).c;
    const out=((y+1)*24+x+offset)*4;
    color.copy(canvas,out);canvas[out+3]=255;
  }
  const filename=a.id+'-v1.png';
  await sharp(canvas,{raw:{width:24,height:24,channels:4}}).png().toFile(path.join(root,filename));
  const seen=new Set();for(let i=0;i<canvas.length;i+=4)if(canvas[i+3])seen.add(canvas.subarray(i,i+3).toString('hex'));
  report.push({id:reviewId(a),asset:a.id,file:filename,size:[24,24],mode:'RGBA',opaque_colors:seen.size,alpha:[0,255],palette:paletteFor(a),source_crop:crop,silhouette_export:[width,22],sha256:crypto.createHash('sha256').update(fs.readFileSync(path.join(root,filename))).digest('hex')});
}

async function sheet(filename,title,rows){
  const width=720,height=52+rows.length*274+28;
  let svg=`<svg width="${width}" height="${height}"><rect width="${width}" height="${height}" fill="#29313d"/><g fill="#e8e9ed" font-family="Arial"><text x="20" y="27" font-size="17">${title}</text>`;
  const layers=[];
  for(let r=0;r<rows.length;r++)for(let c=0;c<rows[r].length;c++){
    const item=rows[r][c],x=20+c*234,y=52+r*274;
    svg+=`<text x="${x}" y="${y+14}" font-size="14">${item.label}</text>`;
    layers.push({input:await sharp(item.file).resize(192,192,{kernel:'nearest'}).png().toBuffer(),left:x+10,top:y+25});
    layers.push({input:item.file,left:x+94,top:y+230});
  }
  svg+=`<text x="20" y="${height-12}" font-size="12">8x preview + actual 24x24 below. Transparent PNGs. Pending approval; not installed.</text></g></svg>`;
  await sharp(Buffer.from(svg)).composite(layers).png().toFile(path.join(root,filename));
}

async function main(){
  fs.mkdirSync(path.join(root,'sources'),{recursive:true});
  for(const a of assets)await exportAsset(a);
  const row=job=>assets.filter(a=>a.job===job&&a.id!=='hesk-durran').map(a=>({label:`${reviewId(a)} / ${a.species.toUpperCase()}`,file:path.join(root,a.id+'-v1.png')}));
  await sheet('approval-workers.png','PLANETARY NPCS / MINERS AND DOCKWORKERS',[row('miner'),row('dockworker')]);
  await sheet('approval-civic.png','PLANETARY NPCS / SECURITY AND POLITICIANS',[row('security'),row('politician')]);
  await sheet('approval-hesk.png','NAMED CHARACTER / HESK DURRAN',[[
    {label:'Approved Muroth Foreman',file:path.resolve(root,'../foreman-v1/muroth-foreman-v1.png')},
    {label:'H1 Hesk Durran',file:path.join(root,'hesk-durran-v1.png')},
  ]]);
  fs.writeFileSync(path.join(root,'validation.json'),JSON.stringify(report,null,2)+'\n');
  console.log(report.map(r=>`${r.id}: ${r.file}, 24x24 RGBA, ${r.opaque_colors} opaque colors`).join('\n'));
}
main().catch(e=>{console.error(e);process.exit(1)});
