import {Capacitor,CapacitorHttp,registerPlugin} from '@capacitor/core';
import {backendOrigin} from './security.mjs';
import type {User} from './types';
export const origin=backendOrigin(import.meta.env.VITE_API_BASE_URL||'https://school-choice-app-hrvb.vercel.app',import.meta.env.DEV);
const secure=registerPlugin<{read():Promise<{value:string|null}>;write(options:{value:string}):Promise<void>;clear():Promise<void>}>('TKSecureStorage');
let token='';
export async function restoreSession(){if(Capacitor.isNativePlatform())token=(await secure.read()).value||'';}
export async function clearSession(){token='';if(Capacitor.isNativePlatform())await secure.clear();}
export async function api<T>(path:string,method='GET',body?:unknown):Promise<T>{
 if(!/^\/[a-zA-Z0-9/_?=&%.,:+-]*$/.test(path))throw new Error('Invalid API path.');
 const url=origin+'/mobile/v1'+path,headers:Record<string,string>={'Content-Type':'application/json'};
 if(token)headers.Authorization='Bearer '+token;
 let status:number,result:Record<string,unknown>;
 if(Capacitor.isNativePlatform()){const r=await CapacitorHttp.request({url,method,headers,data:body,responseType:'json',connectTimeout:15000,readTimeout:20000});status=r.status;result=r.data;}
 else{const r=await fetch(url,{method,headers,credentials:'omit',cache:'no-store',body:body===undefined?undefined:JSON.stringify(body)});status=r.status;try{result=await r.json();}catch{throw new Error('This server does not have the mobile API yet. Use an approved mobile preview backend.');}}
 if(status===401){await clearSession();document.dispatchEvent(new Event('tk:session-expired'));}
 if(status<200||status>=300)throw new Error(String(result?.error||'The request could not be completed. Please try again.'));
 return result as T;
}
export async function signIn(body:Record<string,unknown>,signup=false){const r=await api<{token:string;user:User}>('/auth/'+(signup?'signup':'login')+'/','POST',{...body,platform:Capacitor.getPlatform()});token=r.token;try{if(Capacitor.isNativePlatform())await secure.write({value:token});}catch{try{await api('/auth/logout/','POST',{});}finally{await clearSession();}throw new Error('Your session could not be stored securely. Sign-in was cancelled.');}return r.user;}
export async function signOut(){try{await api('/auth/logout/','POST',{});}finally{await clearSession();document.dispatchEvent(new Event('tk:session-expired'));}}
