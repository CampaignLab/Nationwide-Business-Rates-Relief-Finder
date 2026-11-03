import {existsSync} from 'node:fs';
import {stageDataset} from './dataset.mjs';
const args=process.argv.slice(2);
if(!args[0]||args.some((a,i)=>i>0&&a!=='--include-downloads'))throw new Error('Usage: npm run prepare-data -- <pipeline-output-folder> [--include-downloads]');
const target=new URL('../web/dataset/',import.meta.url);
if(existsSync(target))throw new Error('web/dataset already exists. Move it aside before preparing a replacement.');
const count=await stageDataset(args[0],target,args.includes('--include-downloads'));
console.log(`Prepared ${count} constituencies for publication. Review web/dataset before deploying.`);
