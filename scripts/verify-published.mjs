import {readFile,access} from 'node:fs/promises';
import {validateIndex} from '../web/data.js';
import {parseProperties} from '../web/csv.js';
const root=new URL('../web/dataset/',import.meta.url);
const index=validateIndex(JSON.parse(await readFile(new URL('constituency_index.json',root),'utf8')));
let count=0;
for(const seat of index.constituencies){
  for(const path of Object.values(seat.files||{}))await access(new URL(path,root));
  if(!seat.files?.csv)continue;
  const rows=parseProperties(await readFile(new URL(seat.files.csv,root),'utf8'));
  if(rows.length!==seat.counts.target_new_full_relief)throw new Error(`Count mismatch: ${seat.code}`);
  for(const row of rows){
    const rv=Number(row.rateable_value);
    if(row.constituency_code!==seat.code||!(rv>index.cohort.lower_rv_exclusive&&rv<=index.cohort.upper_rv_inclusive)||!['retail','hospitality','leisure','pub'].includes(row.sector)||row.target_new_full_relief!=='True'||Number(row.relief_from_apr_2027)!==1)throw new Error(`Invalid target property in ${seat.code}`);
  }
  count+=rows.length;
}
console.log(`Verified ${count.toLocaleString('en-GB')} published property rows across ${index.constituencies.length} constituencies.`);

