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
    if(!Object.hasOwn(row,'primary_description')||!Object.hasOwn(row,'secondary_description')||!Object.hasOwn(row,'scat_description')||row.scat_category!==row.scat_code.slice(0,3))throw new Error(`Missing or inconsistent VOA code display: ${seat.code}`);
    if(!row.use_review_group||!Object.hasOwn(row,'secondary_description_code')||!Object.hasOwn(row,'review_categories'))throw new Error(`Missing classifier evidence fields: ${seat.code}`);
    if(row.screening_outcome==='needs_review'&&!row.review_categories)throw new Error(`Review without structured reasons: ${seat.code}`);
    if(row.screening_outcome==='likely_candidate'&&(row.review_categories||row.use_review_group!=='clear_recorded_use'))throw new Error(`Likely candidate has review conflicts: ${seat.code}`);
    if(row.constituency_code!==seat.code||!(rv>index.cohort.lower_rv_exclusive&&rv<=index.cohort.upper_rv_inclusive)||!['likely_candidate','needs_review'].includes(row.screening_outcome)||!row.screening_reason||!/^https?:\/\//.test(row.council_url))throw new Error(`Invalid screened property in ${seat.code}`);
  }
  for(const outcome of ['likely_candidate','needs_review'])if(rows.filter(r=>r.screening_outcome===outcome).length!==seat.counts[outcome])throw new Error(`Screening count mismatch: ${seat.code}`);
  if(new Set(rows.map(r=>r.property_reference)).size!==rows.length)throw new Error(`Duplicate property: ${seat.code}`);
  count+=rows.length;
}
console.log(`Verified ${count.toLocaleString('en-GB')} published property rows across ${index.constituencies.length} constituencies.`);

