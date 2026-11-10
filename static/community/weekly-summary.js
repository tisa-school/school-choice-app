/* Real-family facts remain server-authoritative. The AI sees anonymous counts only. */
document.addEventListener('DOMContentLoaded',async()=>{
 const card=document.querySelector('[data-live-weekly="true"]');if(!card)return;
 try{const response=await fetch('/family/weekly-summary/',{method:'POST',credentials:'same-origin',headers:{'X-CSRFToken':document.querySelector('meta[name="csrf-token"]').content},signal:AbortSignal.timeout(12000)});if(!response.ok)return;const result=await response.json();if(result.source!=='ai'||typeof result.commentary!=='string')return;const target=card.querySelector('[data-weekly-comment]'),badge=document.createElement('span'),text=document.createElement('p');badge.className='status-pill';badge.textContent=document.documentElement.lang==='pt-PT'?'✦ Resumo semanal IA':'✦ AI weekly summary';text.textContent=result.commentary;text.dataset.userContent='';target.replaceChildren(badge,text);}catch(_){/* Keep the factual card available. */}
});
