/* Real account permissions are enforced by the upload endpoint. */
(()=>{'use strict';
document.addEventListener('submit',async event=>{
 const form=event.target.closest('[data-team-upload]');if(!form)return;
 event.preventDefault();if(form.dataset.busy)return;
 const buttons=[...form.querySelectorAll('button')],status=form.querySelector('[data-upload-status]');
 form.dataset.busy='true';buttons.forEach(button=>button.disabled=true);form.setAttribute('aria-busy','true');status.textContent='…';
 try{
  const data=new FormData(form);if(event.submitter?.value==='delete'){data.set('action','delete');data.delete('image');}
  const response=await fetch(form.getAttribute('action'),{method:'POST',body:data,headers:{'X-Requested-With':'XMLHttpRequest'},credentials:'same-origin'});
  if(response.redirected){window.location.assign(response.url);return;}
  const result=await response.json();if(!response.ok)throw new Error(result.error||response.statusText);
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
  document.dispatchEvent(new CustomEvent('team-portrait-updated',{detail:{id:form.dataset.person,photo}}));
 }catch(error){status.textContent=error.message;}
 finally{delete form.dataset.busy;buttons.forEach(button=>button.disabled=false);form.removeAttribute('aria-busy');}
});})();
