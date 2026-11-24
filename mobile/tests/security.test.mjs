import {test} from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {backendOrigin,websitePath,escape,deepLink} from '../src/security.mjs';
test('only HTTPS API origins without embedded credentials, except explicit local development',()=>{
 assert.equal(backendOrigin('https://example.com/'),'https://example.com');
 for(const url of ['http://example.com','https://secret@example.com','https://example.com/api','https://example.com?key=bad'])assert.throws(()=>backendOrigin(url));
 assert.equal(backendOrigin('http://127.0.0.1:8765',true),'http://127.0.0.1:8765');
});
test('website links cannot leave trusted host, carry secrets or inject JavaScript',()=>{
 for(const path of ['/','/events/12/','/schools/example/','/family/calendar/','/accounts/password-reset/'])assert.equal(websitePath(path),path);
 for(const path of ['//evil.com','https://evil.com','/events/12/?token=secret','javascript:alert(1)','/../admin/'])assert.throws(()=>websitePath(path));
});
test('HTML escaped before catalogue and user content is rendered',()=>assert.equal(escape('<img onerror="x">'), '&lt;img onerror=&quot;x&quot;&gt;'));
test('native deep links validate their route',()=>{
 assert.equal(deepLink('org.unicornschool.tkzone://open?path=/events/12/'),'/events/12/');
 assert.throws(()=>deepLink('https://evil.com'));
});
test('release shell is local, HTTPS only, and contains no dev CSP allowance',()=>{
 const config=fs.readFileSync('capacitor.config.ts','utf8');assert.doesNotMatch(config,/server\s*:\s*\{[^}]*url\s*:/);
 assert.match(config,/cleartext:\s*false/);assert.match(config,/webContentsDebuggingEnabled:\s*false/);
 const html=fs.readFileSync('dist/index.html','utf8');assert.doesNotMatch(html,/DEV_CONNECT|CONNECT_ORIGIN|ws:\/\/|http:\/\//);
});
