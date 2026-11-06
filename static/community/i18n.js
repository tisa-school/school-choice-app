/* UI-only translation. User-authored event text and names are never translated. */
(()=>{
 const data=document.getElementById('ui-catalog');let dictionary={};try{dictionary=JSON.parse(data?.textContent||'{}');}catch(_){}
 const markers=/^([✦✧✓♡♥←→↗◇○▦\s]*)(.*?)([✦✧✓♡♥←→↗◇○▦\s]*)$/u;
 let compiled;
 function dynamic(value){if(!compiled)compiled=Object.keys(dictionary).filter(key=>/\{value\d+\}/.test(key)).map(key=>{const parts=key.split(/(\{value\d+\})/);const names=[];const pattern=parts.map(part=>{if(/^\{value\d+\}$/.test(part)){names.push(part);return '(.*?)';}return part.replace(/[.*+?^${}()|[\]\\]/g,'\\$&');}).join('');return {key,names,regex:new RegExp('^'+pattern+'$','s')};});for(const {key,names,regex} of compiled){const match=value.match(regex);if(match){let output=dictionary[key];names.forEach((name,i)=>{output=output.replaceAll(name,match[i+1]);});return output;}}return value;}
 function translate(value){if(dictionary[value])return dictionary[value];const match=value.match(markers);return match&&dictionary[match[2]]?match[1]+dictionary[match[2]]+match[3]:dynamic(value);}
 function localize(root){if(!root)return;const walker=document.createTreeWalker(root,NodeFilter.SHOW_TEXT);const nodes=[];while(walker.nextNode())nodes.push(walker.currentNode);for(const node of nodes){if(node.parentElement?.closest('script,style,textarea,[data-user-content]'))continue;const raw=node.textContent,trim=raw.trim();if(!trim)continue;const translated=translate(trim);if(translated!==trim){if(node.parentElement.tagName==='OPTION'&&!node.parentElement.hasAttribute('value'))node.parentElement.value=trim;node.textContent=raw.replace(trim,translated);}}root.querySelectorAll('[placeholder],[aria-label]').forEach(element=>{if(element.closest('[data-user-content]'))return;for(const attribute of ['placeholder','aria-label'])if(element.hasAttribute(attribute))element.setAttribute(attribute,translate(element.getAttribute(attribute)));});}
 window.TKZoneI18n={text:translate,localize,setDictionary:value=>{dictionary=value;compiled=null;},locale:document.documentElement.dataset.intlLocale||'en-GB'};
 document.addEventListener('DOMContentLoaded',()=>{
  localize(document.body);let pending=false;
  new MutationObserver(entries=>{
   if(pending||!entries.some(entry=>!entry.target.parentElement?.closest('script,style,[data-user-content]')))return;
   pending=true;requestAnimationFrame(()=>{pending=false;localize(document.body);});
  }).observe(document.body,{childList:true,subtree:true});
 });
})();
