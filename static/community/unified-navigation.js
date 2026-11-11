/* One inline navigation on desktop and mobile; no separate mobile destination list. */
document.addEventListener('DOMContentLoaded',()=>{
 const mobile=matchMedia('(max-width:800px)');
 function close(focus=false){document.body.classList.remove('navigation-open');const button=document.querySelector('.nav-menu-toggle');button?.setAttribute('aria-expanded','false');if(focus)button?.focus();}
 document.addEventListener('click',event=>{
  const button=event.target.closest('.nav-menu-toggle');
  if(button){const open=!document.body.classList.contains('navigation-open');document.body.classList.toggle('navigation-open',open);button.setAttribute('aria-expanded',String(open));if(open)document.querySelector('.unified-navigation a')?.focus();}
  else if(event.target.closest('.unified-navigation a'))close();
 });
 document.addEventListener('keydown',event=>{if(event.key==='Escape'&&document.body.classList.contains('navigation-open')){event.preventDefault();close(true);}});
 document.addEventListener('tkzone:render',()=>close());
 mobile.addEventListener('change',()=>close());
});
