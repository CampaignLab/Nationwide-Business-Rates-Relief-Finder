import {readFile,writeFile,mkdir,copyFile,realpath} from 'node:fs/promises';
import {resolve,relative,isAbsolute,dirname,sep} from 'node:path';
import {fileURLToPath} from 'node:url';
import {validateIndex} from '../web/data.js';
export async function stageDataset(input,output,includeDownloads=false){
  const root=await realpath(input instanceof URL?fileURLToPath(input):resolve(input));
  const destination=output instanceof URL?fileURLToPath(output):resolve(output);
  const diff=relative(root,destination);
  if(!diff||(!diff.startsWith(`..${sep}`)&&diff!=='..'&&!isAbsolute(diff)))throw new Error('Destination must be outside the source folder.');
  const indexPath=await realpath(resolve(root,'constituency_index.json'));
  if(relative(root,indexPath).startsWith('..'))throw new Error('Index must be inside the source folder.');
  const data=validateIndex(JSON.parse(await readFile(indexPath,'utf8')));
  data.demo=false;
  const copies=[];
  for(const row of data.constituencies){
    if(!includeDownloads){row.files={};continue;}
    for(const path of Object.values(row.files||{})){
      const source=await realpath(resolve(root,path));
      const rel=relative(root,source);
      if(rel==='..'||rel.startsWith(`..${sep}`)||isAbsolute(rel))throw new Error('Download must be inside the source folder.');
      copies.push([source,resolve(destination,path)]);
    }
  }
  await mkdir(destination,{recursive:true});
  for(const [source,target] of copies){await mkdir(dirname(target),{recursive:true});await copyFile(source,target);}
  await writeFile(resolve(destination,'constituency_index.json'),JSON.stringify(data,null,2));
  return data.constituencies.length;
}
