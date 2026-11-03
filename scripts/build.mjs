import {mkdir,copyFile,rm} from 'node:fs/promises';
import {fileURLToPath} from 'node:url';
import {stageDataset} from './dataset.mjs';
import {existsSync} from 'node:fs';
const root=new URL('../',import.meta.url);
const target=new URL('dist/',root);
await rm(target,{recursive:true,force:true});
await mkdir(target,{recursive:true});
// Explicit allowlist: pipeline data and generated output never enter the deployment.
for(const file of ['index.html','methodology.html','style.css','app.js','data.js','csv.js']) await copyFile(new URL(`web/${file}`,root),new URL(file,target));
if(existsSync(new URL('web/dataset/constituency_index.json',root))) await stageDataset(new URL('web/dataset/',root),new URL('dataset/',target),true);
console.log(`Static app built: ${fileURLToPath(target)}`);
