import {demo,validateIndex,filterRows} from './data.js';
import {parseProperties,filterProperties} from './csv.js';
const $ = id => document.getElementById(id);
const number = new Intl.NumberFormat('en-GB');
let dataset = demo, urls = [];
let properties=[],propertyRequest=0;
function clearUrls(){ urls.forEach(URL.revokeObjectURL); urls=[]; }
function el(tag,text,className){ const node=document.createElement(tag); if(text!==undefined)node.textContent=text;if(className)node.className=className;return node; }
function setDataset(value,files=new Map(),hosted=false){
  clearUrls(); dataset=value; dataset.localFiles=files;dataset.hosted=hosted;
  $('mode').textContent=value.demo?'DEMONSTRATION DATA':hosted?(value.sector_mapping_reviewed===true?'PUBLISHED DATASET':'DRAFT DATASET · SECTOR MAPPING AWAITS REVIEW'):'LOCAL DATA · NOT UPLOADED';
  $('notice').textContent=value.demo?value.notice:'Potential eligibility only. Check with the billing authority. VO restricted licence: use and onward disclosure are restricted. Only use these files as authorised.';
  const cohort=value.cohort;
  $('snapshot').textContent=`RHL properties: rateable value above £${number.format(cohort.lower_rv_exclusive)} and up to £${number.format(cohort.upper_rv_inclusive)} inclusive. Potential full relief from ${cohort.effective_from}. ${value.demo?'Illustrative only.':`Snapshot: ${value.snapshot_epoch ?? 'unknown'} · ${value.file_date ?? 'unknown date'}. ${value.rules_snapshot ?? ''} Sector mapping: ${value.sector_mapping_reviewed===true?'reviewed':'draft / awaiting review'}.`}`;
  $('demo').hidden=!!value.demo;
  $('total').textContent=number.format(value.constituencies.reduce((sum,r)=>sum+r.counts.properties_in_list,0));
  $('flagged').textContent=number.format(value.constituencies.reduce((sum,r)=>sum+r.counts.target_new_full_relief,0));
  $('seats').textContent=number.format(value.constituencies.length);
  $('search').value='';$('region').replaceChildren(new Option('All regions',''));
  [...new Set(value.constituencies.map(r=>r.region))].sort().forEach(r=>$('region').add(new Option(r,r)));
  render();
}
function render(){
  clearUrls();
  const rows=filterRows(dataset.constituencies,$('search').value,$('region').value);
  $('results').textContent=`${number.format(rows.length)} of ${number.format(dataset.constituencies.length)} constituencies${dataset.demo?' · illustrative counts':''}`;
  $('cards').replaceChildren();
  if(!rows.length){$('cards').append(el('p','No constituencies match. Try another name or region.','empty'));return;}
  for(const row of rows){
    const card=el('article',undefined,'card');card.append(el('div',row.region,'region'),el('h3',row.name),el('div',row.code,'code'));
    const dl=el('dl');
    for(const [label,key] of [['Potentially moving to full relief','target_new_full_relief'],['Properties in the list','properties_in_list'],['Tapered SBRR under old model','now_possibly_eligible_now'],['No SBRR under old model','now_not_flagged']]){
      const group=el('div');group.append(el('dt',label),el('dd',number.format(row.counts[key])));dl.append(group);
    }
    card.append(dl);const downloads=el('div',undefined,'downloads');let available=0;
    for(const format of ['csv','xlsx']){
      const path=row.files?.[format];const file=dataset.localFiles?.get(path);if(!file&&!(dataset.hosted&&path))continue;
      const url=file?URL.createObjectURL(file):`/dataset/${path.split('/').map(encodeURIComponent).join('/')}`;if(file)urls.push(url);const a=el('a',`Download ${format==='csv'?'CSV':'Excel'} ↓`);a.href=url;a.download=file?file.name:path.split('/').at(-1);downloads.append(a);available++;
    }
    if(!available)downloads.append(el('span',dataset.demo?'Demo · no property files':'No matching download files selected'));
    if(row.files?.csv&&(dataset.hosted||dataset.localFiles?.has(row.files.csv))){const browse=el('button','View properties');browse.addEventListener('click',()=>openProperties(row));downloads.prepend(browse);}
    card.append(downloads);$('cards').append(card);
  }
}
async function openProperties(row){
  const request=++propertyRequest;properties=[];$('property-search').value='';$('properties').replaceChildren();$('property-title').textContent=row.name;$('property-status').textContent='Loading properties…';$('property-dialog').showModal();
  try{
    const path=row.files.csv;const file=dataset.localFiles?.get(path);
    let text;
    if(file){if(file.size>30*1024*1024)throw new Error('File exceeds the 30 MB browser limit. Use the downloaded file instead.');text=await file.text();}
    else{const response=await fetch(`/dataset/${path.split('/').map(encodeURIComponent).join('/')}`);if(!response.ok)throw new Error('Property file unavailable.');text=await response.text();if(text.length>30*1024*1024)throw new Error('File is too large to browse. Use the download instead.');}
    if(request!==propertyRequest)return;
    properties=parseProperties(text);renderProperties();
  }catch(error){if(request===propertyRequest)$('property-status').textContent=`Could not open properties: ${error.message}`;}
}
function renderProperties(){
  const rows=filterProperties(properties,$('property-search').value);const shown=rows.slice(0,100);
  $('property-status').textContent=`${number.format(rows.length)} matches of ${number.format(properties.length)} flagged properties. Showing ${shown.length}${rows.length>100?' — refine your search for more specific results':''}.`;
  $('properties').replaceChildren();
  for(const row of shown){
    const tr=el('tr');const location=el('td');location.append(el('strong',row.address),el('p',`${row.postcode} · ${row.firm_name||'Occupier not identified'}`));
    const rv=Number(row.rateable_value);const value=el('td',Number.isFinite(rv)?new Intl.NumberFormat('en-GB',{style:'currency',currency:'GBP',maximumFractionDigits:0}).format(rv):row.rateable_value);
    const status=el('td');status.append(el('p',`Now: ${(row.status_now||'unknown').replaceAll('_',' ')}`),el('p',`April 2027: ${(row.status_from_apr_2027||'unknown').replaceAll('_',' ')}`),el('small',row.reason||''));tr.append(location,value,status);$('properties').append(tr);
  }
}
$('close-properties').addEventListener('click',()=>$('property-dialog').close());
$('property-dialog').addEventListener('close',()=>{propertyRequest++;properties=[];$('properties').replaceChildren();});
$('property-search').addEventListener('input',renderProperties);
$('search').addEventListener('input',render);$('region').addEventListener('change',render);
$('demo').addEventListener('click',()=>{setDataset(demo);$('folder').value='';$('file-status').textContent='';});
$('folder').addEventListener('change',async event=>{
  const files=[...event.target.files]; if(!files.length)return;
  $('file-status').textContent='Opening local dataset…';
  try{
    const indexes=files.filter(f=>f.name==='constituency_index.json');
    if(indexes.length!==1)throw new Error('Select the output folder containing exactly one constituency_index.json.');
    const index=indexes[0];if(index.size>5*1024*1024)throw new Error('The index is too large (maximum 5 MB).');
    const data=validateIndex(JSON.parse(await index.text()));
    // A selected local file must never be able to masquerade as the built-in demo.
    data.demo=false;
    const prefix=index.webkitRelativePath.slice(0,-index.name.length);
    const selected=new Map(files.filter(f=>f.webkitRelativePath.startsWith(prefix)).map(f=>[f.webkitRelativePath.slice(prefix.length),f]));
    setDataset(data,selected);$('file-status').textContent='Dataset opened locally. Refresh or return to demo to clear it.';
  }catch(error){$('file-status').textContent=`Could not open dataset: ${error.message}`;}
});
setDataset(demo);
// Optional deployment dataset. A missing dataset leaves the clearly labelled demo.
try{
  const response=await fetch('/dataset/constituency_index.json');
  if(response.ok){const data=validateIndex(await response.json());data.demo=false;setDataset(data,new Map(),true);}
  else if(response.status!==404) $('file-status').textContent='Published dataset unavailable. Showing demonstration data.';
}catch{ $('file-status').textContent='Published dataset could not be loaded. Showing demonstration data.'; }
window.addEventListener('pagehide',clearUrls);
