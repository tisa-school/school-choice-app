/* Local preference matching only. Uncertain subject, age or setting means no photo. */
(function(scope){
 const norm=value=>String(value||'').toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g,'');
 const contains=(text,term)=>new RegExp('(^|[^a-z0-9])'+norm(term).replace(/[.*+?^${}()|[\]\\]/g,'\\$&')).test(text);
 const english=v=>typeof v==='object'?(v?.en||''):v||'';
 const fingerprint=e=>[english(e.title),english(e.description),e.minAge??null,e.maxAge??null,e.interest||'',e.area||'',e.venue||'',e.activityEnvironment||'',e.title?.pt||'',e.description?.pt||''];
 function choose(e,spec){
  const curated=spec.demoSelections?.[e.id];
  if(curated&&JSON.stringify(curated.reviewedDetails)===JSON.stringify(fingerprint(e)))return curated.scene;
  const title=norm(english(e.title)),description=norm(english(e.description)),venue=norm(e.venue),context=[title,description,venue,norm(e.area)].join(' ');
  if(!['Lisbon','Lisboa','Alfama','Belém','Graça','Estrela','Alvalade','Campo de Ourique','Parque das Nações'].some(w=>contains(context,w)))return null;
  let setting=e.activityEnvironment||'unspecified';
  const inside=['room','hall','studio','classroom','library','lab','sala','auditorio'].some(w=>contains(venue,w)),outside=['park','garden','pitch','field','parque','jardim','campo'].some(w=>contains(venue,w)),venueSetting=inside&&!outside?'indoor':outside&&!inside?'outdoor':'unspecified';
  if(['indoor','outdoor'].includes(setting)&&['indoor','outdoor'].includes(venueSetting)&&setting!==venueSetting)return null;
  if(!['indoor','outdoor','mixed'].includes(setting)){setting=venueSetting;if(setting==='unspecified'){const text=title+' '+description,inside=['indoor','in a studio','in the studio','numa sala'].some(w=>contains(text,w)),outside=['outdoor','in a park','in the park','ao ar livre'].some(w=>contains(text,w));setting=inside&&!outside?'indoor':outside&&!inside?'outdoor':'unspecified';}}
  if(!Number.isInteger(e.minAge)||!Number.isInteger(e.maxAge)||setting==='unspecified')return null;
  const ranked=[];
  for(const [key,scene] of Object.entries(spec.scenes)){if(!scene.categories.includes(e.interest)||e.minAge>scene.minAge||e.maxAge<scene.maxAge||setting!==scene.setting||scene.exclude.some(w=>contains(title+' '+description,w)))continue;const score=scene.keywords.reduce((n,w)=>n+4*contains(title,w)+2*contains(description,w),0);if(score)ranked.push([score,key]);}
  ranked.sort((a,b)=>b[0]-a[0]||a[1].localeCompare(b[1]));return ranked[0]?.[1]||null;
 }
 const api={choose,fingerprint};if(typeof module!=='undefined')module.exports=api;else scope.TKActivityImagery=api;
})(typeof window!=='undefined'?window:globalThis);
