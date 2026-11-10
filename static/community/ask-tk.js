/* Stateless activity concierge. No storage, analytics or conversation history. */
document.addEventListener('DOMContentLoaded',()=>{
 const launcher=document.createElement('button'),panel=document.createElement('dialog');
 launcher.type='button';launcher.id='ask-tk-launcher';launcher.setAttribute('aria-haspopup','dialog');launcher.setAttribute('aria-controls','ask-tk-panel');launcher.setAttribute('aria-expanded','false');
 panel.id='ask-tk-panel';panel.setAttribute('aria-labelledby','ask-tk-title');panel.dataset.userContent='';
 document.body.append(launcher,panel);let controller=null;
 const t=(en,pt)=>document.documentElement.lang==='pt-PT'?pt:en;
 const label=()=>{launcher.textContent=t('✦ Ask TK','✦ Pergunta ao TK');};label();
 const clear=()=>{controller?.abort();controller=null;panel.replaceChildren();launcher.setAttribute('aria-expanded','false');};
 panel.addEventListener('close',()=>{clear();launcher.focus();});
 function open(){
  label();panel.innerHTML=`<header><div><small>TK-ZONE</small><h2 id="ask-tk-title">${t('✦ Ask TK','✦ Pergunta ao TK')}</h2></div><button type="button" data-tk-close aria-label="${t('Close assistant','Fechar assistente')}">×</button></header><div class="tk-chat-body"><p>${t('What would you like to explore? Try “English-friendly art this weekend”.','O que gostarias de explorar? Experimenta «arte em inglês este fim de semana».')}</p><p class="tk-privacy">${t('Chat stays only on this page and is cleared when closed or refreshed. AI searches are sent to Claude. Do not include names, contacts, addresses or other private details. Ask a parent before using AI.','A conversa fica apenas nesta página e é apagada ao fechar ou atualizar. As pesquisas com IA são enviadas ao Claude. Não incluas nomes, contactos, moradas ou outros dados privados. Pede autorização a um adulto antes de usar IA.')}</p><p class="tk-scope">${location.pathname.startsWith('/demo/')?t('Fictional demo catalogue · no real bookings','Catálogo fictício · sem reservas reais'):t('Suggestions from activities you can view · participation needs parent approval','Sugestões de atividades que podes consultar · a participação precisa de aprovação parental')}</p><form id="tk-chat-form"><label for="tk-question">${t('Your activity question','A tua pergunta sobre atividades')}</label><textarea id="tk-question" maxlength="500" rows="2" required placeholder="${t('Art for an 11-year-old on Saturday…','Arte para uma criança de 11 anos no sábado…')}"></textarea><label class="tk-consent"><input id="tk-consent" type="checkbox" required> <span>${t('I have parent permission and included activity preferences only.','Tenho autorização de um adulto e incluí apenas preferências de atividades.')}</span></label><button class="button" type="submit">${t('Ask with AI ✦','Perguntar com IA ✦')}</button></form><button type="button" class="button secondary" data-tk-browse>${t('Browse catalogue without AI','Explorar catálogo sem IA')}</button><div id="tk-reply" role="status" aria-live="polite" aria-atomic="true"></div><p class="tk-privacy">${t('Activity suggestions only. TK does not book, message organisers or verify safety. Check details with a parent.','Apenas sugestões. O TK não reserva, não contacta organizadores nem verifica a segurança. Confirma os detalhes com um adulto.')}</p></div>`;
  panel.querySelector('[data-tk-close]').addEventListener('click',()=>panel.close());
  panel.querySelector('form').addEventListener('submit',event=>{event.preventDefault();send('ai');});
  panel.querySelector('[data-tk-browse]').addEventListener('click',()=>send('browse'));
  launcher.setAttribute('aria-expanded','true');panel.showModal();panel.querySelector('textarea').focus({preventScroll:true});panel.scrollTop=0;
 }
 launcher.addEventListener('click',open);
 async function send(mode){
  const question=panel.querySelector('textarea'),consent=panel.querySelector('#tk-consent'),reply=panel.querySelector('#tk-reply');
  if(mode==='ai'&&(!question.value.trim()||!consent.checked))return;
  controller?.abort();const pending=new AbortController();controller=pending;
  const controls=[...panel.querySelectorAll('form button,[data-tk-browse]')];controls.forEach(button=>button.disabled=true);
  reply.replaceChildren();reply.textContent=t('Finding activities…','A procurar atividades…');reply.setAttribute('aria-busy','true');
  const timeout=setTimeout(()=>pending.abort(),16000);
  try{
   const response=await fetch('/assistant/ask/',{method:'POST',credentials:'same-origin',headers:{'Content-Type':'application/json','X-CSRFToken':document.querySelector('meta[name="csrf-token"]').content},body:JSON.stringify({preferences:mode==='ai'?question.value.trim():'',consent:mode==='ai'&&consent.checked,scope:location.pathname.startsWith('/demo/')?'demo':'live',mode}),signal:pending.signal});
   if(response.status===429)throw new Error('limit');
   const data=await response.json();if(!response.ok)throw new Error(data.error||'unavailable');
   if(!panel.open||controller!==pending)return;
   let results=data.results||[];
   if(location.pathname.startsWith('/demo/'))document.dispatchEvent(new CustomEvent('tkzone:ask-catalogue',{detail:{filters:data.filters,days:data.days,respond:items=>{results=items;}}}));
   reply.replaceChildren();const heading=document.createElement('p');heading.className='tk-answer';heading.textContent=data.source==='ai'?t('✦ AI understood your preferences. These catalogue activities match:','✦ A IA interpretou as tuas preferências. Estas atividades correspondem:'):t('Catalogue suggestions · AI was not used.','Sugestões do catálogo · sem IA.');reply.append(heading);
   if(!results.length){const empty=document.createElement('p');empty.textContent=t('No matching activities. Try fewer preferences or browse the catalogue.','Sem atividades correspondentes. Experimenta menos preferências ou explora o catálogo.');reply.append(empty);}
   for(const item of results.slice(0,4)){
    if(typeof item.title!=='string'||typeof item.url!=='string'||!/^\/(?:demo\/events\/[a-z0-9-]+|events\/\d+)\/$/.test(item.url))continue;
    const card=document.createElement('article'),link=document.createElement('a'),reason=document.createElement('p');link.href=item.url;link.textContent=item.title;reason.textContent=item.reason||'';card.append(link,reason);reply.append(card);
   }
   if(data.source==='ai')window.TKAIEffects?.type(heading,'ask-tk:'+heading.textContent+performance.now());
   question.value='';consent.checked=false;reply.scrollIntoView({block:'nearest'});
  }catch(error){
   if(!panel.open||controller!==pending)return;
   reply.textContent=error.message==='private'?t('Please remove personal or contact information before asking.','Retira os dados pessoais ou de contacto antes de perguntar.'):error.message==='limit'?t('Please wait a few minutes before asking again.','Espera alguns minutos antes de perguntar novamente.'):t('AI is unavailable or the search could not finish. Try “Browse catalogue without AI”; no credits are needed.','A IA está indisponível ou a pesquisa não terminou. Experimenta «Explorar catálogo sem IA»; não precisas de créditos.');
  }finally{clearTimeout(timeout);if(controller===pending){controller=null;reply.setAttribute('aria-busy','false');controls.forEach(button=>button.disabled=false);}}
 }
 document.addEventListener('tkzone:render',()=>{label();if(panel.open)panel.close();});
 window.addEventListener('pagehide',()=>{if(panel.open)panel.close();clear();});
});
