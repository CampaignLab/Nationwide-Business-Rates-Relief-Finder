const search=document.getElementById('scat-search');
const filter=document.getElementById('scat-filter');
const rows=[...document.querySelectorAll('[data-scat-row]')];
const count=document.getElementById('scat-count');
function applyFilters(){
  const query=search.value.trim().toLowerCase();
  let visible=0;
  for(const row of rows){
    row.hidden=!(row.textContent.toLowerCase().includes(query)&&(!filter.value||row.dataset.flags.split(' ').includes(filter.value)));
    if(!row.hidden)visible++;
  }
  count.textContent=`${visible} of ${rows.length} SCAT codes. A code can appear in more than one classification filter.`;
}
function revealLinkedCode(){
  if(!/^#scat-\d{3}$/.test(location.hash))return;
  const row=document.getElementById(location.hash.slice(1));
  if(!row)return;
  search.value='';filter.value='';applyFilters();
  row.querySelectorAll('details').forEach(detail=>detail.open=true);
  row.scrollIntoView({block:'start'});
}
search.addEventListener('input',applyFilters);
filter.addEventListener('change',applyFilters);
window.addEventListener('hashchange',revealLinkedCode);
applyFilters();revealLinkedCode();
