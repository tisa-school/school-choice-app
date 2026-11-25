import {defineConfig,loadEnv} from 'vite';
import {backendOrigin} from './src/security.mjs';
export default defineConfig(({mode})=>{
 const env=loadEnv(mode,process.cwd(),'VITE_');
 const origin=backendOrigin(env.VITE_API_BASE_URL||'https://school-choice-app-hrvb.vercel.app',mode==='development');
 return {server:{host:'127.0.0.1',port:5173,strictPort:true},build:{target:'es2022'},plugins:[{name:'trusted-connect-origin',transformIndexHtml:html=>html.replace('CONNECT_ORIGIN',origin).replace('DEV_CONNECT',mode==='development'?'ws://127.0.0.1:5173':'')}]};
});
