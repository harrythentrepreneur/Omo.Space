import assert from 'node:assert/strict';
import test from 'node:test';
import {canonicalError, canonicalErrorCode, storefrontRequest} from './run-storefront-helpers.mjs';

test('Facebook uses canonical native Vercel envelope and routes while other workflows retain legacy path',()=>{
 const facebook=storefrontRequest('facebook-ads-copywriter',{offer:'sale'},true);
 assert.deepEqual(facebook,{path:'/v1/runs',pollPath:'/v1/runs/',payload:{contract_version:'1.0',workflow:{slug:'facebook-ads-copywriter',version:'0.1.0'},input:{offer:'sale'}}});
 assert.deepEqual(storefrontRequest('legacy',{brief:'x'},false),{path:'/api/run',pollPath:'/api/run/',payload:{slug:'legacy',fields:{brief:'x'}}});
 assert.deepEqual(storefrontRequest('manifest',{brief:'x'},true).payload,{slug:'manifest',input:{brief:'x'}});
});

test('canonical errors render safe messages and codes, never object coercions',()=>{
 const payment={error:{code:'PAYMENT_REQUIRED',message:'Insufficient balance'}};
 const provider={status:'failed',error:{code:'PROVIDER_FAILED',message:'Workflow runtime reported failure'}};
 assert.equal(canonicalErrorCode(payment),'PAYMENT_REQUIRED');
 assert.equal(canonicalError(payment),'Insufficient balance');
 assert.equal(canonicalError(provider),'Workflow runtime reported failure');
 for(const hostile of [{error:{}},{error:{message:{private:'no'}}},{error:{code:{private:'no'}}}])assert.notEqual(canonicalError(hostile),'[object Object]');
});