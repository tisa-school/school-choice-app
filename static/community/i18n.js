/* UI-only translation. User-authored event text and names are never translated. */
(()=>{
 const data=document.getElementById('ui-catalog');let dictionary={};try{dictionary=JSON.parse(data?.textContent||'{}');}catch(_){}
 const markers=/^([✦✧✓♡♥←→↗◇○▦\s]*)(.*?)([✦✧✓♡♥←→↗◇○▦\s]*)$/u;
 function translate(value){if(dictionary[value])return dictionary[value];const match=value.match(markers);return match&&dictionary[match[2]]?match[1]+dictionary[match[2]]+match[3]:value;}
 function localize(root){if(!root)return;const walker=document.createTreeWalker(root,NodeFilter.SHOW_TEXT);const nodes=[];while(walker.nextNode())nodes.push(walker.currentNode);for(const node of nodes){if(node.parentElement?.closest('script,style,textarea,[data-user-content]'))continue;const raw=node.textContent,trim=raw.trim();if(!trim)continue;const translated=translate(trim);if(translated!==trim){if(node.parentElement.tagName==='OPTION'&&!node.parentElement.hasAttribute('value'))node.parentElement.value=trim;node.textContent=raw.replace(trim,translated);}}root.querySelectorAll('[placeholder],[aria-label]').forEach(element=>{if(element.closest('[data-user-content]'))return;for(const attribute of ['placeholder','aria-label'])if(element.hasAttribute(attribute))element.setAttribute(attribute,translate(element.getAttribute(attribute)));});}
 window.TKZoneI18n={text:translate,localize,locale:document.documentElement.dataset.intlLocale||'en-GB'};
 document.addEventListener('DOMContentLoaded',()=>{localize(document.querySelector('[data-localize-demo]'));const root=document.querySelector('[data-localize-demo]');if(root){let pending=false;new MutationObserver(()=>{if(pending)return;pending=true;requestAnimationFrame(()=>{pending=false;localize(root);});}).observe(root,{childList:true,subtree:true});}});
})();
