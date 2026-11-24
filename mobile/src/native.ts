import {Capacitor,registerPlugin} from '@capacitor/core';
import {Browser} from '@capacitor/browser';
import {PushNotifications} from '@capacitor/push-notifications';
import {App} from '@capacitor/app';
import {SplashScreen} from '@capacitor/splash-screen';
import {Network} from '@capacitor/network';
import {api,origin} from './api';
import {websitePath,deepLink} from './security.mjs';
import type {CalendarItem} from './types';
const calendar=registerPlugin<{present(options:{title:string;start:string;end:string;location:string;url:string}):Promise<{opened?:boolean;saved?:boolean}>}>('TKCalendar');
export async function openWebsite(path:string){const url=origin+websitePath(path);if(Capacitor.isNativePlatform())await Browser.open({url,presentationStyle:'fullscreen'});else window.open(url,'_blank','noopener,noreferrer');}
export async function addCalendar(item:CalendarItem){
 if(item.cancelled||!item.end_at)throw new Error('A valid non-cancelled start and end time is required.');
 if(!Capacitor.isNativePlatform())throw new Error('Open this feature in the iOS or Android app. The website also offers calendar export.');
 await calendar.present({title:item.title,start:item.start_at,end:item.end_at,location:item.location,url:origin+websitePath(item.web_path)});
}
export async function enablePush(){
 if(!Capacitor.isNativePlatform())throw new Error('Push registration requires a real iOS or Android device.');
 const capabilities=await api<{push_configured:Record<string,boolean>}>('/capabilities/');
 if(!capabilities.push_configured[Capacitor.getPlatform()])throw new Error('Push delivery is not configured on this backend yet. Your in-app inbox still works.');
 if((await PushNotifications.requestPermissions()).receive!=='granted')throw new Error('Notifications were not enabled. You can change this in device settings.');
 await PushNotifications.register();
}
export async function disablePush(){await api('/push/device/','DELETE',{});if(Capacitor.isNativePlatform())await PushNotifications.unregister();}
export async function initialiseNative(navigate:(path:string)=>void,notice:(message:string)=>void){
 if(!Capacitor.isNativePlatform())return;
 await SplashScreen.hide();
 await PushNotifications.addListener('registration',async t=>{try{const r=await api<{delivery_configured:boolean}>('/push/device/','POST',{token:t.value,consent:true});notice(r.delivery_configured?'Device registered for notifications.':'Device registered; server delivery still needs setup.');}catch(e){notice(String(e));}});
 await PushNotifications.addListener('registrationError',()=>notice('Push registration failed. No notification was sent.'));
 await PushNotifications.addListener('pushNotificationActionPerformed',()=>navigate('/notifications'));
 await App.addListener('backButton',()=>{if(location.hash&&location.hash!=='#/')history.back();else App.minimizeApp();});
 const handleLink=(url:string)=>{try{const path=deepLink(url);const match=path.match(/^\/events\/(\d+)\/$/);navigate(match?'/event/'+match[1]:'/');}catch{notice('This app link is not supported.');}};
 await App.addListener('appUrlOpen',e=>handleLink(e.url));
 const launch=await App.getLaunchUrl();if(launch?.url)handleLink(launch.url);
 await App.addListener('appStateChange',s=>{document.body.classList.toggle('private-background',!s.isActive);if(s.isActive)document.dispatchEvent(new Event('tk:resume'));});
 await Network.addListener('networkStatusChange',s=>{if(!s.connected)notice('You are offline. Changes need a connection to be saved.');});
}
