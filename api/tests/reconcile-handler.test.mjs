import assert from 'node:assert/strict';
import test from 'node:test';
import handler from '../reconcile-runs.js';

function response(){return {code:0,body:null,status(n){this.code=n;return this},json(v){this.body=v;return this}}}

test('Vercel cron GET reaches authentication rather than method rejection',async()=>{
 const old=process.env.CRON_SECRET;process.env.CRON_SECRET='cron-test';
 try{const res=response();await handler({method:'GET',headers:{authorization:'Bearer wrong'}},res);assert.equal(res.code,401);assert.equal(res.body.error,'unauthorized')}
 finally{if(old===undefined)delete process.env.CRON_SECRET;else process.env.CRON_SECRET=old}
});

test('unsupported cron methods fail closed',async()=>{const res=response();await handler({method:'DELETE',headers:{}},res);assert.equal(res.code,405)});
