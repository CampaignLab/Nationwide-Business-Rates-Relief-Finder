import test from 'node:test';
import assert from 'node:assert/strict';
import {demo,validateIndex,filterRows} from '../web/data.js';
import {parseProperties,filterProperties,exportProperties} from '../web/csv.js';
import {execFileSync} from 'node:child_process';
import {readdirSync} from 'node:fs';
import {mkdtemp,mkdir,writeFile,readFile} from 'node:fs/promises';
import {stageDataset} from '../scripts/dataset.mjs';
import {resolve} from 'node:path';
test('pipeline-shaped index and case-insensitive search',()=>{
  assert.equal(validateIndex(structuredClone(demo)).constituencies.length,6);
  assert.equal(filterRows(demo.constituencies,'  EARLEY ','').length,1);
  assert.equal(filterRows(demo.constituencies,'','London').length,1);
  assert.equal(filterRows(demo.constituencies,'Earley','London').length,0);
});
test('malformed counts, duplicate codes and remote/traversal download paths rejected',()=>{
  for(const mutate of [d=>d.constituencies[0].counts.target_new_full_relief=-1,d=>d.constituencies.push(d.constituencies[0]),d=>d.constituencies[0].files.csv='https://example.com/data.csv',d=>d.constituencies[0].files.csv='constituencies/csv/../data.csv']){
    const data=structuredClone(demo);mutate(data);assert.throws(()=>validateIndex(data));
  }
});
test('accepts existing publisher file paths and empty datasets',()=>{
  const data=structuredClone(demo);data.constituencies[0].files={csv:'constituencies/csv/E14001196_Earley_and_Woodley.csv',xlsx:'constituencies/xlsx/E14001196_Earley_and_Woodley.xlsx'};
  assert.equal(validateIndex(data),data);const empty={cohort:demo.cohort,constituencies:[]};assert.deepEqual(validateIndex(empty),empty);
  assert.throws(()=>validateIndex({constituencies:[]}));
});
test('deployment contains only allowlisted browser files',()=>{
  execFileSync(process.execPath,['scripts/build.mjs'],{cwd:new URL('../',import.meta.url)});
  assert.deepEqual(readdirSync(new URL('../dist/',import.meta.url)).filter(name=>name!=='dataset').sort(),['app.js','csv.js','data.js','index.html','methodology.css','methodology.html','style.css']);
});
test('screening filters combine name, outcome and RV and exported rows match',()=>{
  const rows=[{property_reference:'1',address:'A',status_now:'not_flagged',rateable_value:'12001',screening_outcome:'likely_candidate',trading_name:'Example, Shop'},
    {property_reference:'2',address:'B',status_now:'not_flagged',rateable_value:'18000',screening_outcome:'needs_review',trading_name:'Example Shop'}];
  const filtered=filterProperties(rows,'example',{outcome:'likely_candidate',min:12001,max:18000});
  assert.equal(filtered.length,1);
  assert.equal(filterProperties(rows,'',{outcome:'needs_review',min:12001,max:17999}).length,0);
  assert.deepEqual(parseProperties(exportProperties(filtered,Object.keys(rows[0]),'Potential eligibility only')),filtered);
});
test('property CSV skips notices and handles commas, quotes, BOM and multiline addresses',()=>{
  const rows=parseProperties('\uFEFFNOTICE\r\n"A notice, with a comma"\r\n\r\nproperty_reference,address,postcode,firm_name,status_now\r\n123,"Unit 1, The \"\"Works\"\"\nMain Street",RG1 1AA,Example,likely_eligible_now\r\n');
  assert.equal(rows.length,1);assert.equal(rows[0].address,'Unit 1, The "Works"\nMain Street');
  assert.equal(filterProperties(rows,'rg11aa').length,1);assert.equal(filterProperties(rows,'EXAMPLE').length,1);assert.equal(filterProperties(rows,'missing').length,0);
  assert.throws(()=>parseProperties('invalid headers'));assert.throws(()=>parseProperties('"unfinished'));
});
test('publication stages summaries or selected property files, never the report',async()=>{
  await mkdir(new URL('../.tmp/',import.meta.url),{recursive:true});
  const fixture=await mkdtemp(new URL('../.tmp/publication-',import.meta.url));
  const input=resolve(fixture,'out');await mkdir(resolve(input,'constituencies/csv'),{recursive:true});
  const data=structuredClone(demo);data.constituencies=data.constituencies.slice(0,1);
  data.constituencies[0].files={csv:'constituencies/csv/example.csv'};
  await writeFile(resolve(input,'constituency_index.json'),JSON.stringify(data));
  await writeFile(resolve(input,'constituencies/csv/example.csv'),'original notices and rows');
  await writeFile(resolve(input,'run_report.md'),'must not publish');
  const summary=resolve(fixture,'summary');await stageDataset(input,summary);
  assert.deepEqual(readdirSync(summary),['constituency_index.json']);
  const staged=JSON.parse(await readFile(resolve(summary,'constituency_index.json'),'utf8'));
  assert.deepEqual(staged.constituencies[0].files,{});assert.equal(staged.demo,false);
  const full=resolve(fixture,'full');await stageDataset(input,full,true);
  assert.equal(await readFile(resolve(full,'constituencies/csv/example.csv'),'utf8'),'original notices and rows');
  assert.equal(readdirSync(full).includes('run_report.md'),false);
  await assert.rejects(stageDataset(input,input,true));
});
