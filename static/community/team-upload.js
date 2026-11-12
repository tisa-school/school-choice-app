/* Real account permissions are enforced by the upload endpoint. */
(()=>{'use strict';
document.addEventListener('change',event=>{
 const input=event.target.closest('[data-inline-photo-file]');if(!input)return;
 const preview=input.form.querySelector('[data-inline-photo-preview]');
 preview.hidden=true;preview.removeAttribute('src');
 const file=input.files[0];if(!file||!['image/jpeg','image/png','image/webp'].includes(file.type))return;
 const reader=new FileReader();reader.onload=()=>{if(input.files[0]!==file)return;preview.src=reader.result;preview.hidden=false;};reader.readAsDataURL(file);
});
document.addEventListener('submit',async event=>{
 const form=event.target.closest('[data-team-upload]');if(!form)return;
 event.preventDefault();if(form.dataset.busy)return;
 const buttons=[...form.querySelectorAll('button')],status=form.querySelector('[data-upload-status]');
 form.dataset.busy='true';buttons.forEach(button=>button.disabled=true);form.setAttribute('aria-busy','true');status.textContent='…';
 try{
  const data=new FormData(form);if(event.submitter?.value==='delete'){data.set('action','delete');data.delete('image');}
  const response=await fetch(form.getAttribute('action'),{method:'POST',body:data,headers:{'X-Requested-With':'XMLHttpRequest'},credentials:'same-origin'});
  if(response.redirected){window.location.assign(response.url);return;}
  let result;try{result=await response.json();}catch(_){throw new Error(document.documentElement.lang==='pt-PT'?'Não foi possível guardar a fotografia. Tenta novamente.':'Photo could not be saved. Please try again.');}
  if(!response.ok)throw new Error(result.error||(document.documentElement.lang==='pt-PT'?'Não foi possível guardar a fotografia.':'Photo could not be saved.'));
  const container=form.closest('article')||form.closest('.lead-panel');
  let image=container.querySelector('.team-portrait');
  let photo=null;
  if(result.deleted){
   if(image){const placeholder=document.createElement('div');placeholder.className='team-symbol';placeholder.setAttribute('aria-hidden','true');placeholder.textContent='✦';image.replaceWith(placeholder);}
   form.querySelector('[data-delete-portrait]').hidden=true;
  }else{
  if(!image){image=document.createElement('img');image.className='team-portrait';image.width=128;image.height=160;const placeholder=container.querySelector('.abstract-avatar,.team-symbol');if(placeholder)placeholder.replaceWith(image);else container.prepend(image);}
  image.src=result.url+'?v='+Date.now();image.alt=result.description;
  photo={url:result.url,description:result.description};form.querySelector('[data-delete-portrait]').hidden=false;
  }
  status.textContent=result.message;form.reset();
  const label=form.querySelector('[data-inline-photo-label]');
  if(label?.firstChild)label.firstChild.textContent=document.documentElement.lang==='pt-PT'?(result.deleted?'Adicionar fotografia':'Alterar fotografia'):(result.deleted?'Add photo':'Change photo');
  const preview=form.querySelector('[data-inline-photo-preview]');
  if(preview){preview.hidden=true;preview.removeAttribute('src');}
  document.dispatchEvent(new CustomEvent('team-portrait-updated',{detail:{id:form.dataset.person,photo}}));
 }catch(error){status.textContent=error.name==='TypeError'?(document.documentElement.lang==='pt-PT'?'Não foi possível guardar a fotografia. Verifica a ligação e tenta novamente.':'Photo could not be saved. Check the connection and try again.'):error.message;}
 finally{delete form.dataset.busy;buttons.forEach(button=>button.disabled=false);form.removeAttribute('aria-busy');}
});})();
