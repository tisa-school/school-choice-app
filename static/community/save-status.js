/* A confirmed timestamp comes only from a successful server-side save receipt. */
(()=>{'use strict';
 const banner=document.getElementById('saved-data-status');if(!banner)return;
 let dictionary={};try{dictionary=JSON.parse(document.getElementById('ui-catalog')?.textContent||'{}');}catch(_){}
 const t=value=>dictionary[value]||value;
 const summary=banner.querySelector('[data-save-summary]');
 const failed=()=>{banner.dataset.saveState='failed';summary.textContent=t('Change not saved. Your last confirmed save is shown below.');};
 document.addEventListener('tkzone:saving',()=>{banner.dataset.saveState='saving';summary.textContent=t('Saving changes…');});
 document.addEventListener('tkzone:save-failed',failed);
 document.addEventListener('tkzone:saved',event=>{
  const receipt=event.detail,date=new Date(receipt?.saved_at);
  if(!receipt||typeof receipt.action!=='string'||!Number.isFinite(date.getTime())){failed();return;}
  const shown=date.toLocaleString(document.documentElement.dataset.intlLocale||undefined);
  banner.dataset.savedAt=receipt.saved_at;banner.dataset.savedAction=receipt.action;banner.dataset.saveState='saved';
  summary.textContent='✓ '+t('Saved to database')+' · '+shown;
  const time=banner.querySelector('[data-save-time]');time.dateTime=receipt.saved_at;time.textContent=shown;
  banner.querySelector('[data-save-action]').textContent=receipt.action;
  banner.querySelector('[data-save-confirmed]').hidden=false;banner.querySelector('[data-save-empty]').hidden=true;
 });
})();
