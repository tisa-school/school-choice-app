export function backendOrigin(value,development=false){
 const u=new URL(value);
 if(u.username||u.password||u.search||u.hash||(u.pathname!=='/'&&u.pathname!==''))throw new Error('Use a backend origin without credentials or a path.');
 if(u.protocol!=='https:'&&!(development&&u.protocol==='http:'&&['127.0.0.1','localhost'].includes(u.hostname)))throw new Error('The backend must use HTTPS.');
 return u.origin;
}
export function websitePath(value){
 if(typeof value!=='string'||value.length>300||!/^\/(?:$|events\/\d+\/$|schools\/(?:[a-z0-9-]+\/)?$|(?:about|privacy|terms|safety|help|family|profile|notifications|organizer|staff|manage|tickets|saved|collections|finder|calendar|community|announcements|join)\/(?:[a-z0-9/-]*)?$|accounts\/(?:login|signup|password-reset)\/$)/.test(value))throw new Error('Unsupported website destination.');
 return value;
}
export function deepLink(value){const u=new URL(value);if(u.protocol!=='org.unicornschool.tkzone:'||u.hostname!=='open')throw new Error('Unsupported app link.');return websitePath(u.searchParams.get('path')||'/');}
export function escape(value){return String(value??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));}
