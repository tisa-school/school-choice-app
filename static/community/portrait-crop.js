document.addEventListener('DOMContentLoaded',()=>{
 for(const form of document.querySelectorAll('[data-portrait-editor]')){
  const file=form.querySelector('[data-crop-file]'),canvas=form.querySelector('canvas'),notice=form.querySelector('[data-photo-notice]');let image=null;
  function draw(){if(!image)return;const value=(axis,fallback)=>Number(form.querySelector('[data-crop-axis="'+axis+'"]').value||fallback);const zoom=value('zoom',1),side=Math.min(image.width,image.height)/zoom,x=(image.width-side)*value('x',.5),y=(image.height-side)*value('y',.5);canvas.hidden=false;canvas.getContext('2d').drawImage(image,x,y,side,side,0,0,canvas.width,canvas.height);}
  file?.addEventListener('change',()=>{const item=file.files[0];if(!item)return;if(!['image/jpeg','image/png','image/webp'].includes(item.type)||item.size>3*1024*1024){notice.textContent=document.documentElement.lang==='pt-PT'?'Escolha uma imagem JPG, PNG ou WebP até 3 MB.':'Choose a JPG, PNG or WebP image up to 3 MB.';file.value='';return;}const reader=new FileReader();reader.onload=()=>{image=new Image();image.onload=()=>{notice.textContent='';draw();};image.onerror=()=>notice.textContent=document.documentElement.lang==='pt-PT'?'Não foi possível pré-visualizar esta imagem.':'This image could not be previewed.';image.src=reader.result;};reader.readAsDataURL(item);});
  form.querySelectorAll('[data-crop-axis]').forEach(control=>control.addEventListener('input',draw));
  form.addEventListener('submit',event=>{if(event.submitter?.value!=='delete'&&!form.checkValidity())return;form.setAttribute('aria-busy','true');notice.textContent=document.documentElement.lang==='pt-PT'?'A guardar…':'Saving…';});
 }
});
