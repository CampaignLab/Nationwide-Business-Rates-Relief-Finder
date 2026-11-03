import {demo,validateIndex,filterRows} from './data.js';
import {parseProperties,filterProperties,exportProperties} from './csv.js';
const $ = id => document.getElementById(id);
const number = new Intl.NumberFormat('en-GB');
let dataset = demo, urls = [];
let properties=[],propertyRequest=0,filteredUrl;
function clearUrls(){ urls.forEach(URL.revokeObjectURL); urls=[]; }
function el(tag,text,className){ const node=document.createElement(tag); if(text!==undefined)node.textContent=text;if(className)node.className=className;return node; }
function setDataset(value,files=new Map(),hosted=false){
  if(!value.demo&&value.screening_version!==1)throw new Error('This dataset predates candidate/review screening. Rebuild the pipeline before opening it.');
  clearUrls(); dataset=value; dataset.localFiles=files;dataset.hosted=hosted;
  $('mode').textContent=value.demo?'DEMONSTRATION DATA':hosted?(value.sector_mapping_reviewed===true?'PUBLISHED DATASET':'DRAFT DATASET · SECTOR MAPPING AWAITS REVIEW'):'LOCAL DATA · NOT UPLOADED';
  $('notice').textContent=value.notice;
  const cohort=value.cohort;
  $('snapshot').textContent=`RHL properties: rateable value above £${number.format(cohort.lower_rv_exclusive)} and up to £${number.format(cohort.upper_rv_inclusive)} inclusive. Potential full relief from ${cohort.effective_from}. ${value.demo?'Illustrative only.':`Snapshot: ${value.snapshot_epoch ?? 'unknown'} · ${value.file_date ?? 'unknown date'}. ${value.rules_snapshot ?? ''} Sector mapping: ${value.sector_mapping_reviewed===true?'reviewed':'draft / awaiting review'}.`}`;
  $('demo').hidden=!!value.demo;
  $('total').textContent=number.format(value.constituencies.reduce((sum,r)=>sum+(r.counts.likely_candidate||0),0));
  $('flagged').textContent=number.format(value.constituencies.reduce((sum,r)=>sum+(r.counts.needs_review||0),0));
  const report=value.screening_report;
  $('screening-summary').textContent=report?`${number.format(report.unassigned_review)} additional assessments need review because no exact English constituency match was found. They are retained in the national review download and are not assigned approximately.`:'';
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
    for(const [label,key] of [['Likely candidates','likely_candidate'],['Possible candidates','needs_review']]){
      const group=el('div');group.append(el('dt',label),el('dd',number.format(row.counts[key]||0)));dl.append(group);
    }
    card.append(dl);const downloads=el('div',undefined,'downloads');let available=0;
    for(const format of ['csv','xlsx']){
      const path=row.files?.[format];const file=dataset.localFiles?.get(path);if(!file&&!(dataset.hosted&&path))continue;
      const url=file?URL.createObjectURL(file):`/dataset/${path.split('/').map(encodeURIComponent).join('/')}`;if(file)urls.push(url);const a=el('a',`All candidates + review (${format==='csv'?'CSV':'Excel'}) ↓`);a.href=url;a.download=file?file.name:path.split('/').at(-1);downloads.append(a);available++;
    }
    if(!available)downloads.append(el('span',dataset.demo?'Demo · no property files':'No matching download files selected'));
    if(row.files?.csv&&(dataset.hosted||dataset.localFiles?.has(row.files.csv))){const browse=el('button','View properties');browse.addEventListener('click',()=>openProperties(row));downloads.prepend(browse);}
    card.append(downloads);$('cards').append(card);
  }
}
async function openProperties(row){
  const request=++propertyRequest;properties=[];$('property-search').value='';$('property-outcome').value='likely_candidate';$('rv-min').value='12001';$('rv-max').value='18000';$('filtered-download').hidden=true;$('properties').replaceChildren();$('property-title').textContent=row.name;$('property-status').textContent='Loading properties…';$('property-dialog').showModal();
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
  const rows=filterProperties(properties,$('property-search').value,{outcome:$('property-outcome').value,min:Number($('rv-min').value||12001),max:Number($('rv-max').value||18000)});const shown=rows.slice(0,100);
  const likely=properties.filter(r=>r.screening_outcome==='likely_candidate').length;
  $('property-status').textContent=`${number.format(rows.length)} matching property assessments · ${likely} likely candidates and ${properties.length-likely} possible candidates in this file. Showing ${shown.length}${rows.length>100?' — refine your search for more specific results':''}.`;
  if(filteredUrl)URL.revokeObjectURL(filteredUrl);
  filteredUrl=URL.createObjectURL(new Blob([exportProperties(rows,Object.keys(properties[0]||{}),dataset.notice)],{type:'text/csv;charset=utf-8'}));
  $('filtered-download').href=filteredUrl;$('filtered-download').download='filtered-property-assessments.csv';$('filtered-download').hidden=!rows.length;
  $('properties').replaceChildren();
  for(const row of shown){
    const firm=(row.firm_name||'').trim();const usableFirm=firm.length>1&&!['unknown','n/a','not known'].includes(firm.toLowerCase());
    const tr=el('tr');const location=el('td');location.append(el('strong',row.trading_name||(usableFirm?firm:row.address)));
    if(row.trading_name||usableFirm)location.append(el('p',row.address));
    location.append(el('p',`${row.postcode} · ${row.description_text||row.sector}`));
    const codes=el('div');codes.setAttribute('aria-label','VOA property classification');
    codes.append(el('p',`SCAT: ${row.scat_category||row.scat_code?.slice(0,3)||'Not recorded'} — ${row.scat_description||'Category description unavailable'}${row.scat_code?` (original: ${row.scat_code})`:''}`));
    codes.append(el('p',`Primary: ${row.primary_description_code||row.description_code||'Not recorded'} — ${row.primary_description||'Description unavailable'}`));
    codes.append(el('p',`Secondary: ${row.secondary_description_code?`${row.secondary_description_code} — ${row.secondary_description||'Description unavailable'}`:'None recorded'}`));
    if(row.description_code&&row.description_code!==row.primary_description_code)codes.append(el('small',`Original description code: ${row.description_code}`));
    location.append(codes);
    if(row.trading_name)location.append(el('small',`Trading name: ${row.name_verification_status?.replaceAll('_',' ')} · ${row.name_source} · recorded ${row.name_recorded_date}`));
    if(row.firm_name)location.append(el('p',`Original VOA firm name: ${row.firm_name}`));
    if(!row.trading_name&&!usableFirm)location.append(el('small','Occupier not identified'));
    const rv=Number(row.rateable_value);const value=el('td',Number.isFinite(rv)?new Intl.NumberFormat('en-GB',{style:'currency',currency:'GBP',maximumFractionDigits:0}).format(rv):row.rateable_value);
    const status=el('td');status.append(el('strong',({'likely_candidate':'Likely candidate','needs_review':'Possible candidate'})[row.screening_outcome]||'Unscreened legacy record'),el('p',row.screening_reason||'Rerun the pipeline to screen this record.'));
    const groups={clear_recorded_use:'Clear recorded use; check other warnings',possible_exclusion:'Possible excluded activity',conditional_use:'Conditional or mixed use',generic_shop:'Generic shop: actual activity unknown',uncertain_sector:'Uncertain sector mapping',property_evidence:'Property evidence needs checking'};
    if(row.screening_outcome==='needs_review'&&row.use_review_group)status.append(el('p',`Use assessment: ${groups[row.use_review_group]||row.use_review_group}`));
    if(row.review_categories)status.append(el('small',`Checks: ${row.review_categories.split(';').map(s=>s.replaceAll('_',' ')).join(' · ')}`));
    if(/^https?:\/\//.test(row.council_url||'')){const link=el('a',`Confirm with ${row.billing_authority}`);link.href=row.council_url;link.target='_blank';link.rel='noopener noreferrer';status.append(link,el('p','Official council homepage · find business rates'));}
    tr.append(location,value,status);$('properties').append(tr);
  }
}
$('close-properties').addEventListener('click',()=>$('property-dialog').close());
const propertyDialog=$('property-dialog');
const outsidePropertyDialog=event=>{
  const box=propertyDialog.getBoundingClientRect();
  return event.clientX<box.left||event.clientX>box.right||event.clientY<box.top||event.clientY>box.bottom;
};
let backdropPress=false;
propertyDialog.addEventListener('pointerdown',event=>{backdropPress=event.target===propertyDialog&&outsidePropertyDialog(event);});
propertyDialog.addEventListener('click',event=>{
  if(backdropPress&&event.target===propertyDialog&&outsidePropertyDialog(event))propertyDialog.close();
  backdropPress=false;
});
$('property-dialog').addEventListener('close',()=>{propertyRequest++;properties=[];$('properties').replaceChildren();if(filteredUrl)URL.revokeObjectURL(filteredUrl);filteredUrl=null;});
$('property-search').addEventListener('input',renderProperties);
for(const id of ['property-outcome','rv-min','rv-max'])$(id).addEventListener('input',renderProperties);
$('search').addEventListener('input',render);$('region').addEventListener('change',render);
$('demo').addEventListener('click',()=>{setDataset(demo);$('file-status').textContent='';});
setDataset(demo);
// Optional deployment dataset. A missing dataset leaves the clearly labelled demo.
try{
  const response=await fetch('/dataset/constituency_index.json');
  if(response.ok){const data=validateIndex(await response.json());data.demo=false;setDataset(data,new Map(),true);}
  else if(response.status!==404) $('file-status').textContent='Published dataset unavailable. Showing demonstration data.';
}catch{ $('file-status').textContent='Published dataset could not be loaded. Showing demonstration data.'; }
window.addEventListener('pagehide',clearUrls);
