/* Guest lists contain public item IDs only. Account saves remain server-authorised. */
document.addEventListener('DOMContentLoaded',()=>{
 const account=document.body.dataset.accountSaves==='true',keys={activity:'tk-discovery-activities-v1',school:'tk-discovery-schools-v1',experience:'tk-discovery-experiences-v1',compare:'tk-discovery-compare-v1'};
 const t=(en,pt)=>document.documentElement.lang==='pt-PT'?pt:en;
 const notice=document.createElement('div');notice.className='discovery-toast';notice.setAttribute('role','status');notice.setAttribute('aria-live','polite');document.body.append(notice);
 function say(message){notice.textContent=message;clearTimeout(say.timer);say.timer=setTimeout(()=>notice.textContent='',5500);}
 const valid=value=>typeof value==='string'&&/^[a-zA-Z0-9_-]{1,190}$/.test(value);
 function read(kind){try{const data=JSON.parse(localStorage.getItem(keys[kind])||'[]');return Array.isArray(data)?[...new Set(data.filter(valid))].slice(0,kind==='compare'?4:100):[];}catch(_){return [];}}
 function write(kind,data){localStorage.setItem(keys[kind],JSON.stringify(data));}
 function sync(){
  for(const kind of ['activity','school','experience'])for(const button of document.querySelectorAll(`[data-save-${kind}]`)){
   const id=button.dataset[{activity:'saveActivity',school:'saveSchool',experience:'saveExperience'}[kind]];
   if(!account)button.setAttribute('aria-pressed',String(read(kind).includes(id)));
   button.classList.toggle('is-saved',button.getAttribute('aria-pressed')==='true');
  }
  const selected=read('compare');document.querySelectorAll('[data-compare-school]').forEach(input=>input.checked=selected.includes(input.dataset.compareSchool));
  document.querySelectorAll('[data-open-comparison]').forEach(link=>link.href='/schools/compare/'+(selected.length?'?'+selected.map(s=>'school='+encodeURIComponent(s)).join('&'):''));
  let bar=document.getElementById('school-compare-bar');
  if(selected.length){if(!bar){bar=document.createElement('aside');bar.id='school-compare-bar';bar.setAttribute('aria-label',t('Selected schools','Escolas selecionadas'));document.body.append(bar);}bar.replaceChildren();const count=document.createElement('span');count.textContent=`${selected.length}/4 `+t('schools selected','escolas selecionadas');const link=document.createElement('a');link.className='button';link.href='/schools/compare/?'+selected.map(s=>'school='+encodeURIComponent(s)).join('&');link.textContent=t('Compare schools','Comparar escolas');const clear=document.createElement('button');clear.type='button';clear.className='text-link';clear.textContent=t('Clear selection','Limpar seleção');clear.addEventListener('click',()=>{try{write('compare',[]);sync();}catch(_){say(t('Selection could not be saved on this device.','Não foi possível guardar a seleção neste dispositivo.'));}});bar.append(count,link,clear);}else bar?.remove();document.body.classList.toggle('has-school-comparison',selected.length>0);
 }
 async function refreshSaved(){
  const target=document.getElementById('saved-discovery-content');if(!target||account)return;
  target.setAttribute('aria-busy','true');
  try{const query=new URLSearchParams({activities:read('activity').join(','),schools:read('school').join(','),experiences:read('experience').join(',')});const response=await fetch('/discovery/saved/?'+query,{credentials:'same-origin',cache:'no-store'});if(!response.ok)throw new Error();target.innerHTML=await response.text();sync();}catch(_){say(t('Saved items could not load. Please refresh to retry.','Não foi possível carregar os itens. Atualiza para tentar novamente.'));}finally{target.removeAttribute('aria-busy');}
 }
 document.addEventListener('click',async event=>{
  const button=event.target.closest('[data-save-activity],[data-save-school],[data-save-experience]');if(!button)return;event.preventDefault();if(button.disabled)return;
  const kind=button.hasAttribute('data-save-activity')?'activity':button.hasAttribute('data-save-school')?'school':'experience',id=button.dataset[{activity:'saveActivity',school:'saveSchool',experience:'saveExperience'}[kind]];
  if(!valid(id))return;const before=button.getAttribute('aria-pressed')==='true',saved=!before;button.disabled=true;button.setAttribute('aria-busy','true');
  try{
   if(account){const response=await fetch(`/discovery/saves/${kind}/${encodeURIComponent(id)}/`,{method:'POST',credentials:'same-origin',headers:{'Content-Type':'application/json','X-CSRFToken':document.querySelector('meta[name="csrf-token"]').content},body:JSON.stringify({saved})});if(!response.ok)throw new Error();const data=await response.json();if(data.saved!==saved)throw new Error();}
   else{const list=read(kind).filter(s=>s!==id);if(saved){if(list.length>=100)throw new Error();list.push(id);}write(kind,list);}
   document.querySelectorAll(`[data-save-${kind}]`).forEach(other=>{const otherId=other.dataset[{activity:'saveActivity',school:'saveSchool',experience:'saveExperience'}[kind]];if(otherId===id)other.setAttribute('aria-pressed',String(saved));});
   if(account){const summary=document.querySelector('#saved-data-status summary');if(summary)summary.textContent=t('Saved to database','Guardado na base de dados');}
   say(saved?(account?t('Saved to your account.','Guardado na tua conta.'):t('Saved on this device.','Guardado neste dispositivo.')):t('Removed from saved.','Removido dos guardados.'));sync();await refreshSaved();
  }catch(_){button.setAttribute('aria-pressed',String(before));say(t('Not saved. Storage or the connection is unavailable. Please try again.','Não foi guardado. O armazenamento ou a ligação está indisponível. Tenta novamente.'));}
  finally{button.disabled=false;button.removeAttribute('aria-busy');}
 });
 document.addEventListener('change',event=>{
  const input=event.target.closest('[data-compare-school]');if(!input)return;const id=input.dataset.compareSchool;if(!valid(id))return;
  const before=read('compare'),next=before.filter(s=>s!==id);if(input.checked){if(next.length>=4){input.checked=false;say(t('Compare up to four schools. Remove one first.','Compara até quatro escolas. Remove uma primeiro.'));return;}next.push(id);}
  try{write('compare',next);sync();}catch(_){input.checked=before.includes(id);say(t('Selection could not be saved on this device.','Não foi possível guardar a seleção neste dispositivo.'));}
 });
 document.addEventListener('tkzone:render',sync);window.addEventListener('pageshow',sync);sync();refreshSaved();
});
