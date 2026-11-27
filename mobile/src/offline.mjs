// Explicit public snapshots only. Never give this module an API response containing family data.
export const MAX_AGE=7*24*60*60*1000;
const DB='tkzone-public-offline-v1',STORE='listings';
const common=['title','name','description','summary','category','venue','area','city','ages','languages','price','start_at','end_at','accessibility','curriculum','address','hours','fees','fee_year','fee_includes','source','last_checked'];
/** @typedef {{key:string,kind:string,id:number,cached_at:number,expires_at:number,title?:string,name?:string,description?:string,summary?:string,venue?:string,address?:string,city?:string,ages?:string,languages?:string,price?:string,fees?:string,start_at?:string,accessibility?:string,curriculum?:string,source?:string}} PublicListing */
/** @returns {PublicListing} */
export function publicSnapshot(kind,input,now=Date.now()){
 if(!['activity','school'].includes(kind)||input?.public!==true||!Number.isSafeInteger(input.id)||input.id<1)throw new Error('Only verified public listings can be downloaded.');
 const result={key:`${kind}-${input.id}`,kind,id:input.id,cached_at:now,expires_at:now+MAX_AGE};
 for(const key of common){if(typeof input[key]==='string')result[key]=input[key].slice(0,16000);}
 if(kind==='activity'&&!result.title||kind==='school'&&!result.name)throw new Error('This listing has no public title.');
 return result;
}
function database(){return new Promise((resolve,reject)=>{const request=indexedDB.open(DB,1);request.onupgradeneeded=()=>request.result.createObjectStore(STORE,{keyPath:'key'});request.onsuccess=()=>resolve(request.result);request.onerror=()=>reject(new Error('Offline storage is unavailable on this device.'));});}
async function transaction(mode,callback){const db=await database();return new Promise((resolve,reject)=>{const tx=db.transaction(STORE,mode);let output;try{output=callback(tx.objectStore(STORE));}catch(e){db.close();reject(e);return;}tx.oncomplete=()=>{db.close();resolve(output?.result);};tx.onerror=()=>{db.close();reject(new Error('Could not update offline copies.'));};tx.onabort=tx.onerror;});}
export function restoredSnapshot(item,now=Date.now()){
 if(!item||!Number.isFinite(item.cached_at)||!Number.isFinite(item.expires_at)||item.expires_at<=now||item.cached_at>now||item.expires_at-item.cached_at!==MAX_AGE)return null;
 try{const clean=publicSnapshot(item.kind,{...item,public:true},item.cached_at);return clean.key===item.key?clean:null;}catch{return null;}
}
export async function listOffline(){const entries=await transaction('readonly',store=>store.getAll());const now=Date.now();const active=[];for(const item of entries){const clean=restoredSnapshot(item,now);if(!clean)await removeOffline(item.key);else active.push(clean);}return active;}
export async function downloadPublic(kind,input){const entry=publicSnapshot(kind,input);const entries=await listOffline();if(entries.length>=50&&!entries.some(x=>x.key===entry.key))throw new Error('Keep up to 50 offline copies. Remove an older copy first.');await transaction('readwrite',store=>store.put(entry));return entry;}
export async function removeOffline(key){await transaction('readwrite',store=>store.delete(key));}
export async function clearOffline(){await transaction('readwrite',store=>store.clear());}
