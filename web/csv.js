// RFC 4180-style reader, including quoted commas, escaped quotes and newlines.
export function parseProperties(text){
  const records=[];let row=[],field='',quoted=false;
  text=text.replace(/^\uFEFF/,'');
  for(let i=0;i<text.length;i++){
    const c=text[i];
    if(c==='"'){
      if(quoted&&text[i+1]==='"'){field+='"';i++;}else quoted=!quoted;
    }else if(c===','&&!quoted){row.push(field);field='';}
    else if((c==='\n'||c==='\r')&&!quoted){if(c==='\r'&&text[i+1]==='\n')i++;row.push(field);records.push(row);row=[];field='';}
    else field+=c;
  }
  if(quoted)throw new Error('CSV has an unterminated quoted field.');
  if(field||row.length){row.push(field);records.push(row);}
  const start=records.findIndex(r=>r.includes('property_reference')&&r.includes('status_now')&&r.includes('address'));
  if(start<0)throw new Error('CSV is missing the pipeline property headers.');
  const headers=records[start];
  return records.slice(start+1).filter(r=>r.some(Boolean)).map(r=>{
    if(r.length!==headers.length)throw new Error('CSV row length does not match the headers.');
    return Object.fromEntries(headers.map((h,i)=>[h,r[i]]));
  });
}
export function filterProperties(rows,query,{outcome='',min=12001,max=18000}={}){
  const q=query.trim().toLowerCase();const compact=q.replace(/\s/g,'');
  return rows.filter(r=>(!outcome||r.screening_outcome===outcome)&&(!r.rateable_value||(Number(r.rateable_value)>=min&&Number(r.rateable_value)<=max))&&([r.address,r.firm_name,r.trading_name,r.property_reference].some(v=>(v||'').toLowerCase().includes(q))||(r.postcode||'').replace(/\s/g,'').toLowerCase().includes(compact)));
}
export function exportProperties(rows,headers,notice){
  const cell=value=>'"'+String(value??'').replace(/^[=+@-]/,"'$&").replaceAll('"','""')+'"';
  return '\uFEFF'+[notice,'',headers.map(cell).join(','),...rows.map(r=>headers.map(h=>cell(r[h])).join(','))].join('\r\n');
}
