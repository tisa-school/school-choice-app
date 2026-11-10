/* Advisory reports for fictional submissions. Admin decisions remain separate. */
(function(scope){
 const inFlight=new Set();
 const matches=(engine,event,locale)=>event.screening?.signature===engine.screeningSignature(event)&&event.screening.locale===locale;
 async function run(engine,event,locale,apply,force=false){
  const signature=engine.screeningSignature(event),key=event.id+signature+locale;
  if(inFlight.has(key)||(!force&&matches(engine,event,locale)))return;
  inFlight.add(key);
  // Yield so checkpoint recording/rendering cannot recurse synchronously.
  await Promise.resolve();
  let report;
  try{const response=await fetch('/demo/moderation-check/',{method:'POST',credentials:'same-origin',headers:{'Content-Type':'application/json','X-CSRFToken':document.querySelector('meta[name="csrf-token"]').content},body:JSON.stringify({activity:engine.screeningInput(event),locale}),signal:AbortSignal.timeout(15000)});if(!response.ok)throw new Error();report=await response.json();}
  catch(_){report={source:'local',status:'needs_review',flags:[{type:'other',reason:locale==='pt-PT'?'Não foi possível concluir a análise. É necessária revisão manual.':'Screening could not complete. Manual review is required.'}]};}
  apply({type:'SCREEN_RESULT',role:'system',id:event.id,signature,locale,report});inFlight.delete(key);
 }
 scope.TKDemoModeration={matches,run};
})(window);
