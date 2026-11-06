const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');

function fixture({reduced=false}={}) {
  const calls=[]; let callback;
  const element={tagName:'H1',dataset:{},closest:()=>null,querySelector:()=>null,contains:()=>false,getBoundingClientRect:()=>({top:10,bottom:100}),animate:(frames,options)=>{calls.push({frames,options});return {cancel(){this.oncancel?.();}};}};
  const root={querySelectorAll:()=>[element]};
  const context={window:{addEventListener(){}},document:{documentElement:{classList:{contains:()=>false}},addEventListener(){},hidden:false,activeElement:null},matchMedia:()=>({matches:reduced,addEventListener(){}}),localStorage:{getItem:()=>null},location:{pathname:'/demo/events/'},innerHeight:900,MutationObserver:class{observe(){}},IntersectionObserver:class{constructor(cb){callback=cb;}observe(){}unobserve(){}disconnect(){}}};
  context.window.IntersectionObserver=context.IntersectionObserver;
  vm.runInNewContext(fs.readFileSync(__dirname+'/succession.js','utf8'),context);
  return {api:context.window.SuccessionReveal,root,element,calls,enter:()=>callback([{target:element,isIntersecting:true}])};
}
test('reveals once per visit and allows a later route visit',()=>{
  const f=fixture();f.api.scan(f.root,'detail:event-one:1');f.enter();f.enter();assert.equal(f.calls.length,1);
  f.api.scan(f.root,'detail:event-one:1');f.enter();assert.equal(f.calls.length,1);
  f.api.scan(f.root,'detail:event-two:2');f.enter();assert.equal(f.calls.length,2);
  assert.equal(f.calls[0].frames[0].transform,'scale(0.94)');assert.equal(f.calls[0].options.duration,580);
});
test('reduced motion does not create an animation',()=>{
  const f=fixture({reduced:true});f.api.scan(f.root,'detail:1');assert.equal(f.calls.length,0);
});
test('interactive groups are excluded',()=>{
  const f=fixture();f.element.querySelector=()=>({tagName:'BUTTON'});f.api.scan(f.root,'detail:1');assert.equal(f.calls.length,0);
});
