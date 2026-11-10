/* Tab-scoped fictional demo checkpoints. Never writes to the server or localStorage. */
(function(scope){
 const KEY='tkzone-demo-session-v1';
 const fingerprint=engine=>Array.from(JSON.stringify(engine.initial())).reduce((h,c)=>(Math.imul(h,31)+c.charCodeAt(0))|0,0);
 function load(engine,storage){
  const empty={state:engine.initial(),actions:[],context:{},restored:false,warning:false};
  try{
   const raw=storage().getItem(KEY);if(!raw)return empty;
   if(raw.length>1000000)throw new Error('Oversized checkpoint');
   const data=JSON.parse(raw);
   if(data.version!==1||data.seed!==fingerprint(engine)||!Array.isArray(data.actions)||data.actions.length>2000)throw new Error('Stale checkpoint');
   let state=engine.initial();
   for(const action of data.actions){if(!action||typeof action.type!=='string'||action.type==='RESET')throw new Error('Invalid action');const next=engine.reduce(state,action);if(next===state)throw new Error('Invalid action');state=next;}
   const c=data.context||{},context={};
   if(['child','parent','organizer','admin'].includes(c.role))context.role=c.role;
   if(typeof c.view==='string')context.view=c.view;
   if(typeof c.item==='string')context.item=c.item;
   context.presenting=c.presenting===true;
   if(Number.isInteger(c.step)&&c.step>=0&&c.step<9)context.step=c.step;
   context.filters={};if(c.filters&&typeof c.filters==='object')for(const [k,v] of Object.entries(c.filters)){if(['age','interest','area','language','price','q','weekend','day','period'].includes(k)&&typeof v==='string'&&v.length<=500)context.filters[k]=v;}
   if(Array.isArray(c.filters?.interests)&&c.filters.interests.length<=5&&c.filters.interests.every(v=>typeof v==='string'&&v.length<=40))context.filters.interests=c.filters.interests;
   return {state,actions:data.actions,context,restored:true,warning:false};
  }catch(_){return {...empty,warning:true};}
 }
 function save(engine,storage,actions,context){
  try{const raw=JSON.stringify({version:1,seed:fingerprint(engine),actions,context});if(raw.length>1000000||actions.length>2000)return false;storage().setItem(KEY,raw);return true;}catch(_){return false;}
 }
 function record(actions,action){return [...actions,action.type==='ONBOARD'?{type:'ONBOARD',pin:'0000'}:structuredClone(action)];}
 const api={KEY,load,save,record};if(typeof module!=='undefined')module.exports=api;else scope.TKDemoSession=api;
})(typeof window!=='undefined'?window:globalThis);
