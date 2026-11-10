/* Factual weekly counts and suggestions; no provider or storage side effects. */
(function(scope){
 function localParts(now){const values={};for(const p of new Intl.DateTimeFormat('en-GB',{timeZone:'Europe/Lisbon',year:'numeric',month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit',hourCycle:'h23'}).formatToParts(now))values[p.type]=p.value;return {day:`${values.year}-${values.month}-${values.day}`,time:`${values.hour}:${values.minute}`};}
 function summarize(state,engine,now=new Date()){
  const today=localParts(now),monday=new Date(today.day+'T12:00:00Z');monday.setUTCDate(monday.getUTCDate()-(monday.getUTCDay()+6)%7);const end=new Date(monday);end.setUTCDate(end.getUTCDate()+7);
  const startDay=monday.toISOString().slice(0,10),endDay=end.toISOString().slice(0,10);
  const legacy=state.requests.some(r=>!r.requestedAt),rows=legacy?state.requests:state.requests.filter(r=>{const date=new Date(r.requestedAt);if(Number.isNaN(date.valueOf()))return false;const day=localParts(date).day;return day>=startDay&&day<endDay;});
  const requested=new Set(rows.map(r=>r.event)).size,approved=new Set(rows.filter(r=>r.status==='approved').map(r=>r.event)).size;
  const attempted=new Set(state.requests.map(r=>r.event));
  const suggestion=state.events.filter(e=>e.status==='approved'&&!attempted.has(e.id)&&state.profile.age>=e.minAge&&state.profile.age<=e.maxAge&&state.profile.interests.includes(e.interest)&&e.languages.includes('English')&&(e.day>today.day||(e.day===today.day&&e.time>today.time))&&Number(e.capacity)>state.requests.filter(r=>r.event===e.id&&r.status==='approved').length&&!engine.conflicts(state,e)).sort((a,b)=>{if(state.preferences.weekends){const weekend=e=>[0,6].includes(new Date(e.day+'T12:00:00Z').getUTCDay());if(weekend(a)!==weekend(b))return weekend(a)?-1:1;}return (a.day+a.time).localeCompare(b.day+b.time);})[0]||null;
  return {requested,approved,period:legacy?'session':'week',startDay,endDay,suggestion};
 }
 const api={summarize};if(typeof module!=='undefined')module.exports=api;else scope.TKDemoWeekly=api;
})(typeof window!=='undefined'?window:globalThis);
