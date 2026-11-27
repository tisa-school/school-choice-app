import {test} from 'node:test';
import assert from 'node:assert/strict';
import {publicSnapshot,MAX_AGE} from '../src/offline.mjs';
test('public snapshot strips authentication, child/family, review and saved-account fields',()=>{
 const snapshot=publicSnapshot('activity',{public:true,id:4,title:'Public workshop',description:'Public detail',saved:true,token:'secret',child:{name:'Private'},requests:[1],decision_note:'Private',email:'private@example.invalid',sessions:[{child:'Private'}]},1000);
 assert.deepEqual(Object.keys(snapshot).sort(),['cached_at','description','expires_at','id','key','kind','title'].sort());
 assert.equal(snapshot.expires_at,1000+MAX_AGE);
});
test('school snapshot only accepts a public published projection',()=>{
 for(const input of [{id:1,name:'Private'}, {public:false,id:1,name:'Private'}, {public:true,id:-1,name:'No'}, {public:true,id:1}])assert.throws(()=>publicSnapshot('school',input));
 assert.equal(publicSnapshot('school',{public:true,id:2,name:'School',address:'Public address'}).name,'School');
 assert.throws(()=>publicSnapshot('family',{public:true,id:1,title:'Private'}));
});
test('snapshot bounds untrusted text',()=>assert.equal(publicSnapshot('activity',{public:true,id:1,title:'x'.repeat(20000)}).title.length,16000));

test('restored snapshots reject expired, extended or malformed timestamps and strip unexpected data',async()=>{
 const {restoredSnapshot}=await import('../src/offline.mjs');
 const item=publicSnapshot('school',{public:true,id:2,name:'Public school'},1000);
 assert.equal(restoredSnapshot(item,1001).name,'Public school');
 assert.equal(restoredSnapshot(item,1000+MAX_AGE),null);
 assert.equal(restoredSnapshot({...item,expires_at:item.expires_at+1},1001),null);
 assert.equal(restoredSnapshot({...item,cached_at:'yesterday'},1001),null);
 assert.equal(restoredSnapshot({...item,child:'Private'},1001).child,undefined);
});
