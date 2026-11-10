const test=require('node:test'),assert=require('node:assert/strict');
const policy=require('./activity-imagery.js'),spec=require('../../content/activity-imagery.json'),demo=require('./demo-state.js');
const base={title:'Painting with watercolours',description:'Children draw and paint together.',interest:'Arts',area:'Alfama',venue:'Community studio',activityEnvironment:'indoor',minAge:8,maxAge:16};
test('all ten reviewed catalogue records use distinct activity subjects',()=>{
 const actual=demo.initial().events.map(e=>policy.choose(e,spec));
 assert.deepEqual(actual,['drawing','science','maths','football','storytelling','nature','percussion','board-games','paper-crafts','family-market']);
 assert.equal(new Set(actual).size,10);
});
test('park painting and studio painting use different appropriate settings',()=>{
 assert.equal(policy.choose(base,spec),'drawing');
 assert.equal(policy.choose({...base,venue:'Lisbon park',activityEnvironment:'outdoor'},spec),'outdoor-painting');
 assert.equal(policy.choose({...base,venue:'Lisbon studio',activityEnvironment:'outdoor'},spec),null);
});
test('edited seed subjects and translated descriptions lose old curation',()=>{
 const event=demo.initial().events[0];
 assert.equal(policy.choose({...event,title:{en:'Swimming lesson'},description:{en:'Swimming'},interest:'Sports'},spec),null);
 assert.equal(policy.choose({...event,description:{...event.description,pt:'Uma atividade completamente diferente.'}},spec),null);
});
test('unknown details and wrong age ranges get no unrelated photo',()=>{
 for(const changes of [{minAge:14,maxAge:16},{minAge:null},{venue:'',activityEnvironment:''},{area:'Porto',venue:'Community studio'}])assert.equal(policy.choose({...base,...changes},spec),null);
});
test('broad categories cannot substitute digital gaming or piano with unrelated activities',()=>{
 assert.equal(policy.choose({...base,title:'Piano rhythm workshop',description:'Play piano',interest:'Music',minAge:7,maxAge:9},spec),null);
 assert.equal(policy.choose({...base,title:'Video game challenge',description:'Cooperative game on a console',interest:'Gaming',minAge:10,maxAge:12},spec),null);
});
