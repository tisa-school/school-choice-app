document.addEventListener('click',async event=>{
 const button=event.target.closest('[data-share-page]');if(!button)return;
 const t=(en,pt)=>document.documentElement.lang==='pt-PT'?pt:en,status=document.querySelector('[data-share-status]'),url=location.origin+location.pathname;
 button.disabled=true;button.setAttribute('aria-busy','true');
 try{
  if(navigator.share){await navigator.share({title:document.title,url});if(status)status.textContent=t('Sharing completed.','Partilha concluída.');}
  else if(navigator.clipboard?.writeText){await navigator.clipboard.writeText(url);if(status)status.textContent=t('Link copied.','Ligação copiada.');}
  else if(status){status.textContent=t('Copy this public link: ','Copia esta ligação pública: ');const input=document.createElement('input');input.readOnly=true;input.value=url;input.setAttribute('aria-label',t('Public link to copy','Ligação pública para copiar'));status.append(input);input.select();}
 }catch(error){if(status)status.textContent=error.name==='AbortError'?t('Sharing cancelled.','Partilha cancelada.'):t('The link could not be shared. You can copy the page address.','Não foi possível partilhar. Podes copiar o endereço da página.');}
 finally{button.disabled=false;button.removeAttribute('aria-busy');}
});
