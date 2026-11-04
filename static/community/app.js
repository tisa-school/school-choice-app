/* Progressive enhancement: all data mutations remain authenticated server POSTs. */
document.addEventListener('DOMContentLoaded', () => {
  for (const [id, css] of [['text-size','large-text'],['reduce-motion','reduced-motion']]) {
    let enabled=false;
    try { enabled=localStorage.getItem(id)==='true'; } catch (_) {}
    document.documentElement.classList.toggle(css,enabled);
    const control=document.getElementById(id);
    if(control){ control.checked=enabled;control.addEventListener('change',()=>{document.documentElement.classList.toggle(css,control.checked);try{localStorage.setItem(id,String(control.checked));}catch(_){}}); }
  }
  document.querySelectorAll('input[type=password]').forEach(input=>{
    const button=document.createElement('button');button.type='button';button.className='text-button';button.textContent='Show password';button.setAttribute('aria-controls',input.id);button.setAttribute('aria-pressed','false');
    button.addEventListener('click',()=>{const show=input.type==='password';input.type=show?'text':'password';button.textContent=show?'Hide password':'Show password';button.setAttribute('aria-pressed',String(show));});input.after(button);
  });
  const toggle=document.querySelector('.calendar-toggle'),calendar=document.getElementById('calendar');
  toggle?.addEventListener('click',()=>{calendar.hidden=!calendar.hidden;toggle.setAttribute('aria-expanded',String(!calendar.hidden));});
  const day=new URLSearchParams(location.search).get('day');
  if(day)document.querySelectorAll('.calendar-grid a').forEach(a=>{if(new URL(a.href).searchParams.get('day')===day){a.classList.add('selected');a.setAttribute('aria-current','date');}});
  const dialog=document.getElementById('confirmation');let pending=null,submitter=null;
  const copy={profile:['Delete this child profile?','This deletes the private child profile and its participation records. This cannot be undone.'],request:['Make a little plan?','Your request will be sent to school staff. Admission is confirmed only after approval.'],cancel:['Release your spot?','This will cancel your request. You can request again if the event is still accepting requests.'],delete:['Delete this collection?','The collection will be deleted. Your saved events will stay in Saved moments.'],decision:['Save this decision?','The requester will be notified. Capacity will be checked again before a place is confirmed.']};
  document.querySelectorAll('form[data-confirm]').forEach(form=>form.addEventListener('submit',e=>{
    if(form.dataset.confirmed==='true')return;
    e.preventDefault();pending=form;submitter=e.submitter;
    const text=copy[form.dataset.confirm];document.getElementById('confirm-title').textContent=text[0];document.getElementById('confirm-body').textContent=text[1];dialog.showModal();
  }));
  document.getElementById('confirm-cancel').addEventListener('click',()=>dialog.close());
  document.getElementById('confirm-yes').addEventListener('click',()=>{if(!pending)return;pending.dataset.confirmed='true';dialog.close();pending.requestSubmit(submitter);});
  const collection=document.getElementById('add-collection');
  collection?.addEventListener('submit',()=>{collection.action=document.getElementById('collection-choice').value;});
  const schoolSearch=document.getElementById('school-search');
  schoolSearch?.addEventListener('input',()=>{document.querySelectorAll('#id_school option').forEach(o=>{o.hidden=Boolean(o.value&&!o.textContent.toLowerCase().includes(schoolSearch.value.toLowerCase()));});});
  const wizard=document.getElementById('event-form');
  if(wizard){
    let stage=0;const stages=[...wizard.querySelectorAll('[data-stage]')];const steps=[...wizard.querySelectorAll('[data-step]')];
    const show=n=>{stage=n;stages.forEach((s,i)=>s.hidden=i!==n);steps.forEach((b,i)=>{if(i===n)b.setAttribute('aria-current','step');else b.removeAttribute('aria-current');});document.getElementById('previous-step').hidden=n===0;document.getElementById('next-step').hidden=n===3;document.getElementById('save-event').hidden=n!==3;
      if(n===3){const val=id=>document.getElementById('id_'+id)?.value||'';document.getElementById('event-preview').textContent=[val('title'),val('category'),val('start_at').replace('T',' · '),val('venue'),val('description'),val('capacity')?val('capacity')+' capacity':'Unlimited capacity',val('price_text')||'Price on request'].join('\n\n');}
    };
    const valid=()=>[...stages[stage].querySelectorAll('input,select,textarea')].every(e=>e.reportValidity());
    steps.forEach(b=>b.addEventListener('click',()=>{const n=Number(b.dataset.step);if(n<stage||valid())show(n);}));
    document.getElementById('next-step').addEventListener('click',()=>{if(valid())show(Math.min(stage+1,3));});
    document.getElementById('previous-step').addEventListener('click',()=>show(Math.max(stage-1,0)));
    wizard.addEventListener('invalid',e=>{const section=e.target.closest('[data-stage]');if(section)show(Number(section.dataset.stage));},true);
    const error=wizard.querySelector('.errorlist');if(error?.closest('[data-stage]'))show(Number(error.closest('[data-stage]').dataset.stage));
  }
  document.getElementById('preview-note')?.addEventListener('click',()=>{document.getElementById('preview-title').textContent=document.getElementById('id_title').value||'Your headline goes here.';document.getElementById('preview-body').textContent=document.getElementById('id_body').value||'Your words, beautifully organized.';});
  document.querySelectorAll('form').forEach(form=>form.addEventListener('submit',()=>{if(form.dataset.confirm&&!form.dataset.confirmed)return;if(!form.checkValidity())return;const button=form.querySelector('button[type=submit]');if(button){button.setAttribute('aria-busy','true');}}));
});

// Save feedback is scoped to write forms. Only the server's receipt confirms persistence.
document.addEventListener('DOMContentLoaded',()=>{
  document.querySelectorAll('form').forEach(form=>{
    if((form.getAttribute('method')||'get').toLowerCase()!=='post')return;
    const path=new URL(form.getAttribute('action')||location.href,location.href).pathname;
    if(path.startsWith('/accounts/')||path==='/finder/')return;
    const state=document.createElement('p');state.className='form-save-status';state.setAttribute('role','status');state.setAttribute('aria-live','polite');state.hidden=true;form.append(state);
    if(form.querySelector('.errorlist')){state.hidden=false;state.dataset.state='unsaved';state.textContent='Not saved · check the highlighted errors and submit again.';}
    const dirty=()=>{state.hidden=false;state.dataset.state='unsaved';state.textContent='Unsaved changes · submit this form to save.';};
    form.addEventListener('input',dirty);form.addEventListener('change',dirty);
    form.addEventListener('submit',()=>{
      if(!form.checkValidity()||(form.dataset.confirm&&form.dataset.confirmed!=='true'))return;
      state.hidden=false;state.dataset.state='saving';state.textContent='Saving to database…';form.setAttribute('aria-busy','true');
    });
    window.addEventListener('pageshow',()=>{form.removeAttribute('aria-busy');if(state.dataset.state==='saving'){state.hidden=false;state.dataset.state='unknown';state.textContent='Save status not confirmed on this page. Check your saved data before trying again.';}});
  });
});
