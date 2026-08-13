import assert from 'node:assert/strict';
import test from 'node:test';
import {createMemoryServices, handleRun, reconcileRuns} from '../v1/runs.js';

const auth={authenticate:async()=>({userId:'user_verified123'})};
const baseEnv={NEON_DATABASE_URL:'configured',MODAL_UGC_ENDPOINT:'https://ugc.modal.test/run',MODAL_FACEBOOK_ADS_ENDPOINT:'https://modal.test/v1/runs',MODAL_PROXY_TOKEN_ID:'id',MODAL_PROXY_TOKEN_SECRET:'secret'};
const ugc={contract_version:'1.0',workflow:{slug:'ugc-script-studio'},input:{product_url:'https://example.com/item',brand_voice:'honest',length:30}};
const facebookInput={product_name:'Northstar Skillet',offer:'A cast-iron skillet with free shipping',audience:'Busy home cooks seeking easier dinners',objective:'sales',tone:'direct',proof_points:'Pre-seasoned and oven-safe',constraints:''};
const facebook={contract_version:'1.0',workflow:{slug:'facebook-ads-copywriter',version:'0.1.0'},input:facebookInput};
const modalResult={status:'completed',result:{hook:'h',shots:['s'],captions:['c'],cta:'go'}};
function response(){return {code:0,body:null,status(code){this.code=code;return this},json(body){this.body=body;return this}}}
async function post(body,services,fetcher,env=baseEnv,key='regression_12345678'){const out=response();await handleRun({method:'POST',headers:{'idempotency-key':key},body},out,env,fetcher,{...auth,store:services.store});return out}
function onlyRow(services){return [...services.snapshot().runs.values()][0]}

 test('owner GET succeeds with injected auth/store and no database or Modal configuration',async()=>{
  const services=createMemoryServices();
  const row={run_id:'run_ownerget123',user_id:'user_verified123',request_hash:'x',slug:'ugc-script-studio',workflow_version:'1.0.0',cost_cents:15,execution_status:'queued',billing_status:'reserved',input:ugc.input,created_at:'2026-08-13T00:00:00.000Z',updated_at:'2026-08-13T00:00:00.000Z',attempt_count:0,artifacts:[]};
  await services.store.claim(row.user_id,'owner_get_key','x',row);
  const out=response();let calls=0;
  await handleRun({method:'GET',headers:{},query:{run_id:row.run_id}},out,{},async()=>{calls++},{...auth,store:services.store});
  assert.equal(out.code,202);assert.equal(out.body.id,row.run_id);assert.equal(calls,0);
 });

test('hostile async result URLs are rejected without credentialed fetch to attacker',async()=>{
 const hostile=['https://attacker.test/v1/runs/call_1','https://user@modal.test/v1/runs/call_1','ftp://modal.test/v1/runs/call_1','https://modal.test:444/v1/runs/call_1','https://modal.test/v1/runs/call_1?q=x','https://modal.test/v1/runs/call_1#x','https://modal.test/wrong/call_1'];
 for(const [index,result_url] of hostile.entries()){
  const services=createMemoryServices({balanceCents:100});const calls=[];
  await post(facebook,services,async(url,options={})=>{calls.push({url,headers:options.headers});return {ok:true,json:async()=>({call_id:'call_1',result_url,status:'accepted'})}},baseEnv,`hostile_${index}_12345678`);
  const row=onlyRow(services);assert.equal(row.error.code,'INVALID_PROVIDER_OUTPUT');assert.equal(row.attempt_count,1);
  assert.deepEqual(calls.map(call=>call.url),[baseEnv.MODAL_FACEBOOK_ADS_ENDPOINT]);
  assert.equal(calls.some(call=>new URL(call.url).hostname==='attacker.test'&&call.headers?.['modal-secret']),false);
 }
});

test('retry recovers before MAX with exponential backoff and correct attempt count',async()=>{
 const services=createMemoryServices({balanceCents:100});let calls=0;
 await post(ugc,services,async()=>{calls++;throw Error('network')});
 const row=onlyRow(services);assert.equal(row.attempt_count,1);assert.equal(row.execution_status,'queued');
 const firstDelay=new Date(row.next_attempt_at)-new Date(row.updated_at);assert.ok(firstDelay>0&&firstDelay<=1100);
 row.next_attempt_at='2000-01-01T00:00:00.000Z';
 await reconcileRuns(services.store,baseEnv,async()=>{calls++;return {ok:false,status:503}});
 assert.equal(row.attempt_count,2);const secondDelay=new Date(row.next_attempt_at)-new Date(row.updated_at);assert.ok(secondDelay>1000&&secondDelay<=2100);
 row.next_attempt_at='2000-01-01T00:00:00.000Z';
 await reconcileRuns(services.store,baseEnv,async()=>{calls++;return {ok:true,json:async()=>modalResult}});
 assert.equal(calls,3);assert.equal(row.attempt_count,3);assert.equal(row.execution_status,'succeeded');assert.deepEqual(services.snapshot().ledger.map(x=>x.kind),['run_debit']);
});

test('retry exhaustion is terminal after three attempts and refunds exactly once',async()=>{
 const services=createMemoryServices({balanceCents:100});let calls=0;const fail=async()=>{calls++;throw Error('network')};
 await post(ugc,services,fail);const row=onlyRow(services);
 for(let attempt=2;attempt<=3;attempt++){row.next_attempt_at='2000-01-01T00:00:00.000Z';await reconcileRuns(services.store,baseEnv,fail)}
 await reconcileRuns(services.store,baseEnv,fail);await reconcileRuns(services.store,baseEnv,fail);
 assert.equal(calls,3);assert.equal(row.attempt_count,3);assert.equal(row.execution_status,'failed');assert.equal(row.error.code,'PROVIDER_UNAVAILABLE');assert.equal(services.snapshot().balanceCents,100);assert.deepEqual(services.snapshot().ledger.map(x=>x.kind),['run_debit','run_refund']);
});

test('mixed configuration skips due workflow rows without endpoint and preserves state',async()=>{
 const services=createMemoryServices({balanceCents:100});const timestamp='2026-08-13T00:00:00.000Z';
 const row={run_id:'run_mixedconfig1',user_id:'user_verified123',request_hash:'x',slug:'facebook-ads-copywriter',workflow_version:'0.1.0',cost_cents:10,execution_status:'queued',billing_status:'reserved',input:facebookInput,created_at:timestamp,updated_at:timestamp,attempt_count:0,artifacts:[]};
 await services.store.claim(row.user_id,'mixed_config_key','x',row);let calls=0;
 const count=await reconcileRuns(services.store,{...baseEnv,MODAL_FACEBOOK_ADS_ENDPOINT:''},async()=>{calls++});
 assert.equal(count,0);assert.equal(calls,0);assert.equal(row.execution_status,'queued');assert.equal(row.attempt_count,0);assert.equal(row.billing_status,'reserved');assert.deepEqual(services.snapshot().ledger,[]);
});
