/* Visual-only AI accents. Complete answers stay in the accessibility tree from the start. */
(()=>{
 const media=matchMedia('(prefers-reduced-motion: reduce)'),answers=new Set(),glows=new Set(),sparks=new Set(),running=new Map();
 const reduced=()=>{let saved=false;try{saved=localStorage.getItem('reduce-motion')==='true';}catch(_){}return media.matches||saved||document.documentElement.classList.contains('reduced-motion');};
 function finish(node){const active=running.get(node);if(!active)return;cancelAnimationFrame(active.frame);active.visual.remove();active.full.style.opacity='1';node.classList.remove('ai-typing');running.delete(node);}
 function type(node,key){
  if(!node)return;finish(node);const text=node.textContent;if(!text||reduced()||answers.has(key)||!node.isConnected)return;
  const box=node.getBoundingClientRect();if(box.bottom<0||box.top>innerHeight)return;
  answers.add(key);finish(node);
  const full=document.createElement('span'),visual=document.createElement('span');full.className='ai-complete-text';full.textContent=text;visual.className='ai-visual-text';visual.setAttribute('aria-hidden','true');node.replaceChildren(full,visual);node.classList.add('ai-typing');
  const glyphs=Array.from(text),start=performance.now(),duration=Math.min(1800,Math.max(650,glyphs.length*12)),entry={full,visual,frame:0};running.set(node,entry);
  const tick=now=>{if(!node.isConnected){finish(node);return;}if(reduced()){finish(node);return;}const progress=Math.min(1,(now-start)/duration);visual.textContent=glyphs.slice(0,Math.ceil(progress*glyphs.length)).join('');if(progress===1)finish(node);else entry.frame=requestAnimationFrame(tick);};entry.frame=requestAnimationFrame(tick);
 }
 function decorate(root=document){
  root.querySelectorAll('.hero').forEach(hero=>{const key=location.pathname;hero.dataset.aiGlow=!reduced()&&!glows.has(key)?'animate':'still';glows.add(key);});
  root.querySelectorAll('[data-ai-accent], [data-ai-fill], [data-action="ai-explain"], [data-action="retry-screen"]').forEach(node=>{
   const key=location.pathname+':'+node.textContent.trim();
   for(const text of [...node.childNodes]){if(text.nodeType!==Node.TEXT_NODE||!text.textContent.includes('✦'))continue;const parts=text.textContent.split('✦'),fragment=document.createDocumentFragment();parts.forEach((part,index)=>{if(index){const star=document.createElement('span');star.className='ai-sparkle';star.textContent='✦';if(!reduced()&&!sparks.has(key))star.dataset.aiShimmer='true';fragment.append(star);}fragment.append(document.createTextNode(part));});text.replaceWith(fragment);}
   sparks.add(key);
  });
 }
 function finishAll(){for(const node of [...running.keys()])finish(node);}
 media.addEventListener('change',()=>{if(reduced())finishAll();});
 new MutationObserver(()=>{if(reduced())finishAll();}).observe(document.documentElement,{attributes:true,attributeFilter:['class']});
 document.addEventListener('DOMContentLoaded',()=>decorate());document.addEventListener('tkzone:render',()=>{for(const node of [...running.keys()])if(!node.isConnected)finish(node);decorate(document.getElementById('demo-app')||document);});
 document.addEventListener('keydown',event=>{if(event.key==='Escape')finishAll();});window.addEventListener('pagehide',finishAll);
 window.TKAIEffects={type,decorate,finishAll};
})();
