import crypto from 'node:crypto';
import inputSchema from '../../containers/ugc-script-studio/generated/schemas/input.json' with {type:'json'};
import outputSchema from '../../containers/ugc-script-studio/generated/schemas/output.json' with {type:'json'};
import manifest from '../../containers/ugc-script-studio/generated/capability-manifest.json' with {type:'json'};
import requestEnvelopeSchema from '../schemas/run-request-v1.schema.json' with {type:'json'};
import runSchema from '../schemas/run-v1.schema.json' with {type:'json'};
import errorSchema from '../schemas/error-v1.schema.json' with {type:'json'};
import artifactSchema from '../schemas/artifact-v1.schema.json' with {type:'json'};
import facebookManifest from '../../containers/facebook-ads-copywriter/manifest.json' with {type:'json'};
import facebookInputSchema from '../../containers/facebook-ads-copywriter/schemas/input.json' with {type:'json'};
import facebookOutputSchema from '../../containers/facebook-ads-copywriter/schemas/output.json' with {type:'json'};

const IDEM=/^[A-Za-z0-9._:-]{8,128}$/;
const RUN_ID=/^run_[A-Za-z0-9]+$/;
const LEASE_MS=2*60*1000;
const MAX_ATTEMPTS=3;
const CONTRACT_VERSION='1.0';
const WORKFLOWS={
 [manifest.slug]:{manifest,inputSchema,outputSchema,costCents:15,endpointKey:'MODAL_UGC_ENDPOINT',async:false},
 [facebookManifest.slug]:{manifest:{slug:facebookManifest.slug,workflow_version:facebookManifest.version,poll_path_template:facebookManifest.endpoint.poll_path_template},inputSchema:facebookInputSchema,outputSchema:facebookOutputSchema,costCents:10,endpointKey:'MODAL_FACEBOOK_ADS_ENDPOINT',async:true},
};
const now=()=>new Date().toISOString();
const send=(res,status,body)=>res.status(status).json(validatePublicBody(body));
const stable=value=>Array.isArray(value)?`[${value.map(stable).join(',')}]`:value&&typeof value==='object'?`{${Object.keys(value).sort().map(k=>`${JSON.stringify(k)}:${stable(value[k])}`).join(',')}}`:JSON.stringify(value);
const hash=value=>crypto.createHash('sha256').update(value).digest('hex');

function validObject(value){return value!==null&&typeof value==='object'&&!Array.isArray(value)}
function issue(path,code,message){return {path,code,message}}
function validateSchema(schema,value,path=''){
 const issues=[];
 if(schema.$ref){
  if(schema.$ref==='artifact-v1.schema.json')return validateSchema(artifactSchema,value,path);
  return [issue(path,'unsupported_ref','Schema reference is not supported')];
 }
 if(schema.const!==undefined&&!Object.is(value,schema.const))return [issue(path,'const',`Expected ${schema.const}`)];
 if(schema.anyOf){return schema.anyOf.some(s=>validateSchema(s,value,path).length===0)?[]:[issue(path,'any_of','Value does not match an allowed shape')]}
 if(schema.type==='null')return value===null?[]:[issue(path,'type','Expected null')];
 if(schema.type==='object'){
  if(!validObject(value))return [issue(path,'type','Expected object')];
  for(const key of schema.required||[])if(!(key in value))issues.push(issue(`${path}/${key}`,'required','Required property is missing'));
  if(schema.additionalProperties===false)for(const key of Object.keys(value))if(!(key in (schema.properties||{})))issues.push(issue(`${path}/${key}`,'additional_property','Additional properties are not allowed'));
  for(const [key,child] of Object.entries(schema.properties||{}))if(key in value)issues.push(...validateSchema(child,value[key],`${path}/${key}`));
 }else if(schema.type==='array'){
  if(!Array.isArray(value))issues.push(issue(path,'type','Expected array'));else{if(value.length<(schema.minItems||0)||value.length>(schema.maxItems??Infinity))issues.push(issue(path,'length','Array length is outside allowed bounds'));value.forEach((v,i)=>issues.push(...validateSchema(schema.items||{},v,`${path}/${i}`)))}
 }else if(schema.enum){if(!schema.enum.some(v=>Object.is(v,value)))issues.push(issue(path,'enum','Value is not in the allowed set'));
 }else if(schema.type==='string'){if(typeof value!=='string')issues.push(issue(path,'type','Expected string'));else if(value.length<(schema.minLength||0)||value.length>(schema.maxLength??Infinity))issues.push(issue(path,'length','String length is outside allowed bounds'));
 }else if(schema.type==='number'&&!(typeof value==='number'&&Number.isFinite(value)))issues.push(issue(path,'type','Expected finite number'));
 else if(schema.type==='integer'&&!Number.isInteger(value))issues.push(issue(path,'type','Expected integer'));
 else if(schema.type==='boolean'&&typeof value!=='boolean')issues.push(issue(path,'type','Expected boolean'));
 return issues;
}
function validateRunInvariants(body){
 if(body.status==='succeeded'){
  if(!validObject(body.result)||body.error!==null)return [issue('/status','invalid_state','Succeeded runs require a result and no error')];
  const outputIssues=validateSchema(WORKFLOWS[body.workflow?.slug]?.outputSchema||outputSchema,body.result,'/result');if(outputIssues.length)return outputIssues;
 }else if(body.status==='failed'){
  if(body.result!==null||!validObject(body.error))return [issue('/status','invalid_state','Failed runs require an error and no result')];
 }else if(body.result!==null||body.error!==null){
  return [issue('/status','invalid_state','Queued and running runs cannot include a result or error')];
 }
 return [];
}
function validatePublicBody(body){
 const isError=body?.error&&!body.contract_version;
 const schema=isError?errorSchema:runSchema;
 const issues=validateSchema(schema,body,'');
 if(!isError)issues.push(...validateRunInvariants(body));
 if(issues.length)throw new Error(`invalid public response: ${JSON.stringify(issues)}`);
 return body;
}
function publicError(code,message,retryable=false,issues=[]){return {error:{contract_version:CONTRACT_VERSION,code,message,retryable,issues}}}
function validateRequest(body){
 let issues=validateSchema(requestEnvelopeSchema,body,'');
 if(issues.length)return issues;
 const workflow=WORKFLOWS[body.workflow.slug];
 if(!workflow||(body.workflow.version!==undefined&&body.workflow.version!==workflow.manifest.workflow_version))return [issue('/workflow','unknown_workflow','Workflow is not available')];
 return validateSchema(workflow.inputSchema,body.input,'/input');
}
function strictProviderResult(data,schema=outputSchema,asyncWorkflow=false){
 if(data?.status!=='completed')return null;
 const result=validObject(data.result)?data.result:(asyncWorkflow?data:null);
 return !result||validateSchema(schema,result,'/result').length?null:result;
}
function publicStatus(row){
 if(row.execution_status==='succeeded')return 'succeeded';
 if(row.execution_status==='failed')return 'failed';
 if(['dispatching','submitted'].includes(row.execution_status))return 'running';
 return 'queued';
}
function normalizeRow(row){
 if(row?.response_json&&!row.response)row.response=typeof row.response_json==='string'?JSON.parse(row.response_json):row.response_json;
 if(row?.accepted_json&&!row.accepted_response)row.accepted_response=typeof row.accepted_json==='string'?JSON.parse(row.accepted_json):row.accepted_json;
 if(row?.input_json&&!row.input)row.input=typeof row.input_json==='string'?JSON.parse(row.input_json):row.input_json;
 if(row?.result_json&&!row.result)row.result=typeof row.result_json==='string'?JSON.parse(row.result_json):row.result_json;
 if(row?.error_json&&!row.error)row.error=typeof row.error_json==='string'?JSON.parse(row.error_json):row.error_json;
 if(row?.artifact_json&&!row.artifacts)row.artifacts=typeof row.artifact_json==='string'?JSON.parse(row.artifact_json):row.artifact_json;
 return row;
}
function runResource(row){
 row=normalizeRow(row);
 return {contract_version:CONTRACT_VERSION,id:row.run_id,workflow:{slug:row.slug,version:row.workflow_version},status:publicStatus(row),created_at:row.created_at,updated_at:row.updated_at,result:row.result||null,artifacts:row.artifacts||[],error:row.error||null};
}
function extractRunId(req){
 if(req.query?.run_id)return String(req.query.run_id);
 const url=String(req.url||'');const match=/\/v1\/runs\/([^/?#]+)/.exec(url)||/\/api\/v1\/runs\/([^/?#]+)/.exec(url);
 return match?decodeURIComponent(match[1]):'';
}

async function authenticateDefault(req,env,fetchImpl){
 const authorization=String(req.headers?.authorization||'').trim();const explicit=String(req.headers?.['x-api-key']||'').trim();const bearer=/^Bearer\s+(.+)$/i.exec(authorization);const credential=explicit||(bearer?.[1]||'');
 if(credential.startsWith('omo_')){if(!env.NEON_DATABASE_URL)return null;const store=await createNeonStore(env);const userId=await store.apiKeyOwner(hash(credential));return userId?{userId,method:'api_key'}:null}
 if(!bearer||!env.CLERK_PUBLISHABLE_KEY)return null;
 try{return {userId:await verifyClerkJwt(bearer[1],env,fetchImpl),method:'clerk'}}catch{return null}
}
function b64url(s){return Buffer.from(s.replace(/-/g,'+').replace(/_/g,'/'),'base64')}
async function verifyClerkJwt(token,env,fetchImpl){
 const parts=token.split('.');if(parts.length!==3)throw Error();const header=JSON.parse(b64url(parts[0]));const claims=JSON.parse(b64url(parts[1]));if(header.alg!=='RS256'||!header.kid)throw Error();
 const encoded=env.CLERK_PUBLISHABLE_KEY.replace(/^pk_(test|live)_/,'');const host=b64url(encoded).toString().replace(/\$$/,'');if(!/^[A-Za-z0-9.-]+$/.test(host))throw Error();
 const response=await fetchImpl(`https://${host}/.well-known/jwks.json`);if(!response.ok)throw Error();const jwk=(await response.json()).keys?.find(k=>k.kid===header.kid);if(!jwk)throw Error();
 const key=crypto.createPublicKey({key:jwk,format:'jwk'});if(!crypto.verify('RSA-SHA256',Buffer.from(`${parts[0]}.${parts[1]}`),key,b64url(parts[2])))throw Error();const t=Math.floor(Date.now()/1000);if(!claims.sub||!/^user_[A-Za-z0-9_-]{3,128}$/.test(claims.sub)||claims.exp<=t||claims.nbf>t||String(claims.iss||'').replace(/\/$/,'')!==`https://${host}`)throw Error();return claims.sub;
}

async function prepareRun(store,row){
 if(row.execution_status!=='claimed')return true;
 if(!await store.reserve(row.user_id,row.cost_cents,row.run_id)){
  await store.paymentFailed(row,{code:'PAYMENT_REQUIRED',message:'Insufficient balance',retryable:false,issues:[]});
  return false;
 }
 await store.markQueued(row);
 return true;
}
async function dispatchRun(store,row,env,fetchImpl){
 if(!await prepareRun(store,row))return;
 const owner=`vercel_${crypto.randomUUID()}`;
 const leased=await store.lease(row.run_id,owner,new Date(Date.now()+LEASE_MS).toISOString());
 if(!leased)return;
 let response,data=null,code='PROVIDER_UNAVAILABLE',message='Workflow runtime is unavailable',retryable=true;
 const workflow=WORKFLOWS[row.slug];const provider=row.response;
 let endpoint=env[workflow.endpointKey],method='POST';
 if(provider){
  try{endpoint=pollUrl(workflow,endpoint,provider);method='GET'}catch{const settled=await store.fail(row.run_id,owner,{code:'INVALID_PROVIDER_OUTPUT',message:'Workflow returned invalid async acceptance',retryable:false,issues:[]},502);if(settled)await store.refund(row.user_id,row.cost_cents,row.run_id);return}
 }
 try{response=await fetchImpl(endpoint,{method,headers:{'content-type':'application/json','modal-key':env.MODAL_PROXY_TOKEN_ID,'modal-secret':env.MODAL_PROXY_TOKEN_SECRET,'x-cognition-run-id':row.run_id},...(method==='POST'?{body:JSON.stringify(row.input)}:{})})}catch{}
 if(response?.ok){try{data=await response.json()}catch{code='INVALID_PROVIDER_OUTPUT';message='Workflow returned invalid JSON';retryable=false}}
 if(workflow.async&&response?.ok&&data&&['accepted','running','queued'].includes(data.status)){
  const acceptance={call_id:data.call_id||provider?.call_id,result_url:data.result_url||provider?.result_url,status:data.status};
  try{pollUrl(workflow,env[workflow.endpointKey],acceptance);await store.markProviderPending(row.run_id,owner,acceptance);return}catch{code='INVALID_PROVIDER_OUTPUT';message='Workflow returned invalid async acceptance';retryable=false}
 }
 const result=strictProviderResult(data,workflow.outputSchema,workflow.async);
 if(result){await store.succeed(row.run_id,owner,result);return}
 if(response?.ok&&data){code=data.status==='failed'?'PROVIDER_FAILED':'INVALID_PROVIDER_OUTPUT';message=data.status==='failed'?'Workflow runtime reported failure':'Workflow returned invalid output';retryable=false}
 if(retryable&&leased.attempt_count<MAX_ATTEMPTS){await store.retry(row.run_id,owner,new Date(Date.now()+1000*2**(leased.attempt_count-1)).toISOString(),provider?'submitted':'queued');return}
 const settled=await store.fail(row.run_id,owner,{code,message,retryable,issues:[]},502);
 if(settled)await store.refund(row.user_id,row.cost_cents,row.run_id);
}

function pollUrl(workflow,endpoint,provider){
 if(!workflow.async||!workflow.manifest.poll_path_template||!/^[-A-Za-z0-9_]{1,128}$/.test(String(provider?.call_id||'')))throw Error('invalid call id');
 const base=new URL(endpoint);if(base.username||base.password||!['https:','http:'].includes(base.protocol))throw Error('invalid endpoint');
 const expected=new URL(workflow.manifest.poll_path_template.replace('{call_id}',encodeURIComponent(provider.call_id)),base.origin);
 if(provider.result_url){const supplied=new URL(provider.result_url,base.origin);if(supplied.username||supplied.password||supplied.origin!==base.origin||supplied.pathname!==expected.pathname||supplied.search||supplied.hash)throw Error('invalid result url')}
 return expected.toString();
}

export async function reconcileRuns(store,env,fetchImpl=fetch,{limit=20}={}){
 const refunds=await store.refundDue(limit);
 for(const row of refunds)await store.refund(row.user_id,row.cost_cents,row.run_id);
 const configuredSlugs=Object.entries(WORKFLOWS).filter(([,workflow])=>env[workflow.endpointKey]).map(([slug])=>slug);
 const rows=await store.due(limit,configuredSlugs);
 for(const row of rows)await dispatchRun(store,normalizeRow(row),env,fetchImpl);
 return refunds.length+rows.length;
}

export function createMemoryServices({balanceCents=500}={}){
 const runs=new Map(),byId=new Map(),ledger=[];let balance=balanceCents;
 const store={
  async claim(userId,key,requestHash,row){const k=`${userId}\0${key}`;if(runs.has(k))return {created:false,row:runs.get(k)};runs.set(k,row);byId.set(row.run_id,row);return {created:true,row}},
  async reserve(userId,cost,runId){if(balance<cost)return false;if(!ledger.some(x=>x.id===`run:${runId}:debit`)){balance-=cost;ledger.push({id:`run:${runId}:debit`,kind:'run_debit',amount:-cost})}return true},
  async getByIdForOwner(userId,runId){const row=byId.get(runId);return row?.user_id===userId?row:null},
  async markQueued(row){row.billing_status='reserved';row.execution_status='queued';row.updated_at=now();row.accepted_response=runResource(row)},
  async markProviderPending(runId,owner,response){const row=byId.get(runId);if(!row||row.dispatch_owner!==owner)return false;row.response=response;row.execution_status='submitted';row.dispatch_owner=null;row.dispatch_lease_expires_at=null;row.updated_at=now();return true},
  async retry(runId,owner,nextAttempt,status){const row=byId.get(runId);if(!row||row.dispatch_owner!==owner)return false;row.execution_status=status;row.dispatch_owner=null;row.dispatch_lease_expires_at=null;row.next_attempt_at=nextAttempt;row.updated_at=now();return true},
  async paymentFailed(row,error){row.execution_status='failed';row.billing_status='unbilled';row.error=error;row.http_status=402;row.updated_at=now()},
  async lease(runId,owner,expires){const row=byId.get(runId);if(!row||['succeeded','failed'].includes(row.execution_status))return null;if(row.dispatch_lease_expires_at&&row.dispatch_lease_expires_at>now()&&row.dispatch_owner&&row.dispatch_owner!==owner)return null;row.dispatch_owner=owner;row.dispatch_lease_expires_at=expires;row.execution_status='dispatching';row.attempt_count=(row.attempt_count||0)+1;row.dispatched_at=now();row.updated_at=row.dispatched_at;return row},
  async due(limit,slugs=Object.keys(WORKFLOWS)){return [...byId.values()].filter(r=>slugs.includes(r.slug)&&!['succeeded','failed'].includes(r.execution_status)&&(!r.dispatch_lease_expires_at||r.dispatch_lease_expires_at<=now())&&(!r.next_attempt_at||r.next_attempt_at<=now())).slice(0,limit)},
  async refundDue(limit){return [...byId.values()].filter(r=>r.billing_status==='refund_due').slice(0,limit)},
  async succeed(runId,owner,result){const row=byId.get(runId);if(!row||row.dispatch_owner!==owner||['succeeded','failed'].includes(row.execution_status))return false;row.execution_status='succeeded';row.billing_status='captured';row.result=result;row.error=null;row.http_status=200;row.updated_at=now();return true},
  async fail(runId,owner,error,httpStatus){const row=byId.get(runId);if(!row||row.dispatch_owner!==owner||['succeeded','failed'].includes(row.execution_status))return false;row.execution_status='failed';row.billing_status='refund_due';row.error=error;row.result=null;row.http_status=httpStatus;row.updated_at=now();return true},
  async refund(userId,cost,runId){const row=byId.get(runId);if(!ledger.some(x=>x.id===`run:${runId}:refund`)){balance+=cost;ledger.push({id:`run:${runId}:refund`,kind:'run_refund',amount:cost})}if(row)row.billing_status='refunded'},
 };
 return {store,snapshot:()=>({balanceCents:balance,ledger:[...ledger],runs})};
}

export async function createNeonStore(env){
 const {Pool}=await import('@neondatabase/serverless');const pool=new Pool({connectionString:env.NEON_DATABASE_URL});
 return {
  async apiKeyOwner(keyHash){const r=await pool.query('SELECT user_id FROM api_keys WHERE key_hash=$1',[keyHash]);return r.rows[0]?.user_id||''},
  async claim(userId,key,requestHash,row){const c=await pool.connect();try{await c.query('BEGIN');const ins=await c.query(`INSERT INTO run_requests (run_id,user_id,idempotency_key,request_hash,slug,workflow_version,cost_cents,execution_status,billing_status,input_json,created_at,updated_at) VALUES ($1,$2,$3,$4,$5,$6,$7,'claimed','unbilled',$8,$9,$10) ON CONFLICT (user_id,idempotency_key) DO NOTHING RETURNING *`,[row.run_id,userId,key,requestHash,row.slug,row.workflow_version,row.cost_cents,JSON.stringify(row.input),row.created_at,row.updated_at]);const found=ins.rowCount?ins:await c.query('SELECT * FROM run_requests WHERE user_id=$1 AND idempotency_key=$2',[userId,key]);await c.query('COMMIT');return {created:!!ins.rowCount,row:normalizeRow(found.rows[0])}}catch(e){await c.query('ROLLBACK');throw e}finally{c.release()}},
  async reserve(userId,cost,runId){const c=await pool.connect();try{await c.query('BEGIN');const dup=await c.query('SELECT event_id FROM credits_ledger WHERE event_id=$1',[`run:${runId}:debit`]);if(dup.rowCount){await c.query('COMMIT');return true}const u=await c.query('UPDATE users SET balance_cents=balance_cents-$1 WHERE user_id=$2 AND balance_cents >= $1 RETURNING balance_cents',[cost,userId]);if(!u.rowCount){await c.query('COMMIT');return false}await c.query('INSERT INTO credits_ledger(event_id,user_id,kind,amount_cents,balance_cents,reference_id,created_at) VALUES($1,$2,$3,$4,$5,$6,$7)',[`run:${runId}:debit`,userId,'run_debit',-cost,u.rows[0].balance_cents,runId,now()]);await c.query("UPDATE run_requests SET billing_status='reserved',updated_at=$1 WHERE run_id=$2 AND billing_status IN ('unbilled','reserved')",[now(),runId]);await c.query('COMMIT');return true}catch(e){await c.query('ROLLBACK');throw e}finally{c.release()}},
  async markQueued(row){row.execution_status='queued';row.billing_status='reserved';row.updated_at=now();row.accepted_response=runResource(row);await pool.query("UPDATE run_requests SET execution_status='queued',billing_status='reserved',accepted_json=$1,updated_at=$2 WHERE run_id=$3 AND execution_status='claimed'",[JSON.stringify(row.accepted_response),row.updated_at,row.run_id])},
  async markProviderPending(runId,owner,response){const r=await pool.query("UPDATE run_requests SET execution_status='submitted',response_json=$1,dispatch_owner=NULL,dispatch_lease_expires_at=NULL,updated_at=$2 WHERE run_id=$3 AND dispatch_owner=$4 AND execution_status='dispatching'",[JSON.stringify(response),now(),runId,owner]);return r.rowCount===1},
  async retry(runId,owner,nextAttempt,status){const r=await pool.query("UPDATE run_requests SET execution_status=$1,dispatch_owner=NULL,dispatch_lease_expires_at=NULL,next_attempt_at=$2,updated_at=$3 WHERE run_id=$4 AND dispatch_owner=$5 AND execution_status='dispatching'",[status,nextAttempt,now(),runId,owner]);return r.rowCount===1},
  async paymentFailed(row,error){row.execution_status='failed';row.billing_status='unbilled';row.error=error;row.http_status=402;row.updated_at=now();await pool.query("UPDATE run_requests SET execution_status='failed',billing_status='unbilled',error_json=$1,http_status=402,updated_at=$2 WHERE run_id=$3 AND execution_status='claimed'",[JSON.stringify(error),row.updated_at,row.run_id])},
  async getByIdForOwner(userId,runId){const r=await pool.query('SELECT * FROM run_requests WHERE user_id=$1 AND run_id=$2',[userId,runId]);return normalizeRow(r.rows[0]||null)},
  async lease(runId,owner,expires){const r=await pool.query("UPDATE run_requests SET execution_status='dispatching',dispatch_owner=$1,dispatch_lease_expires_at=$2,attempt_count=attempt_count+1,dispatched_at=$3,updated_at=$3 WHERE run_id=$4 AND execution_status IN ('queued','submitted','dispatching') AND (dispatch_lease_expires_at IS NULL OR dispatch_lease_expires_at <= $3) RETURNING *",[owner,expires,now(),runId]);return normalizeRow(r.rows[0]||null)},
  async due(limit,slugs){if(!slugs?.length)return [];const r=await pool.query("SELECT * FROM run_requests WHERE slug = ANY($3::text[]) AND execution_status IN ('claimed','queued','submitted','dispatching') AND (dispatch_lease_expires_at IS NULL OR dispatch_lease_expires_at <= $1) AND (next_attempt_at IS NULL OR next_attempt_at <= $1) ORDER BY updated_at LIMIT $2",[now(),limit,slugs]);return r.rows.map(normalizeRow)},
  async refundDue(limit){const r=await pool.query("SELECT * FROM run_requests WHERE billing_status='refund_due' ORDER BY updated_at LIMIT $1",[limit]);return r.rows.map(normalizeRow)},
  async succeed(runId,owner,result){const r=await pool.query("UPDATE run_requests SET execution_status='succeeded',billing_status='captured',result_json=$1,error_json=NULL,http_status=200,updated_at=$2 WHERE run_id=$3 AND dispatch_owner=$4 AND execution_status='dispatching'",[JSON.stringify(result),now(),runId,owner]);return r.rowCount===1},
  async fail(runId,owner,error,httpStatus){const r=await pool.query("UPDATE run_requests SET execution_status='failed',billing_status='refund_due',error_json=$1,result_json=NULL,http_status=$2,updated_at=$3 WHERE run_id=$4 AND dispatch_owner=$5 AND execution_status='dispatching'",[JSON.stringify(error),httpStatus,now(),runId,owner]);return r.rowCount===1},
  async refund(userId,cost,runId){const c=await pool.connect();try{await c.query('BEGIN');const ins=await c.query('INSERT INTO credits_ledger(event_id,user_id,kind,amount_cents,balance_cents,reference_id,created_at) VALUES($1,$2,$3,$4,0,$5,$6) ON CONFLICT(event_id) DO NOTHING RETURNING event_id',[`run:${runId}:refund`,userId,'run_refund',cost,runId,now()]);if(ins.rowCount){const u=await c.query('UPDATE users SET balance_cents=balance_cents+$1 WHERE user_id=$2 RETURNING balance_cents',[cost,userId]);await c.query('UPDATE credits_ledger SET balance_cents=$1 WHERE event_id=$2',[u.rows[0].balance_cents,`run:${runId}:refund`]);await c.query("UPDATE run_requests SET billing_status='refunded',updated_at=$1 WHERE run_id=$2 AND billing_status='refund_due'",[now(),runId])}await c.query('COMMIT')}catch(e){await c.query('ROLLBACK');throw e}finally{c.release()}},
 };
}

async function identityFor(req,env,fetchImpl,deps){
 let identity;try{identity=await (deps.authenticate?deps.authenticate(req,env,fetchImpl):authenticateDefault(req,env,fetchImpl))}catch{return null}
 return identity?.userId?identity:null;
}
export async function handleRun(req,res,env=process.env,fetchImpl=fetch,deps={}){
 const requestedWorkflow=req.method==='POST'&&validObject(req.body)?WORKFLOWS[req.body.workflow?.slug]:null;
 if(!env.NEON_DATABASE_URL&&(req.method!=='GET'||!deps.store))return send(res,503,publicError('SERVER_NOT_CONFIGURED','Run service is not configured',true));
 const identity=await identityFor(req,env,fetchImpl,deps);if(!identity)return send(res,401,publicError('UNAUTHORIZED','Verified Clerk JWT or API key required'));
 let store;try{store=deps.store||await createNeonStore(env)}catch{return send(res,503,publicError('SERVER_NOT_CONFIGURED','Database is unavailable',true))}
 if(req.method==='GET'){
  const runId=extractRunId(req);if(!RUN_ID.test(runId))return send(res,400,publicError('INVALID_REQUEST','A valid run id is required'));
  const row=await store.getByIdForOwner(identity.userId,runId);if(!row)return send(res,404,publicError('NOT_FOUND','Run was not found'));
  const body=runResource(row);return send(res,Number(row.http_status)||(body.status==='succeeded'?200:body.status==='failed'?502:202),body);
 }
 if(req.method!=='POST')return send(res,405,publicError('INVALID_REQUEST','Use POST'));
 const issues=validateRequest(req.body);if(issues.length)return send(res,422,publicError('INVALID_INPUT','Request does not match the canonical workflow contract',false,issues));
 if(!env.MODAL_PROXY_TOKEN_ID||!env.MODAL_PROXY_TOKEN_SECRET||!env[requestedWorkflow.endpointKey])return send(res,503,publicError('SERVER_NOT_CONFIGURED','Run service is not configured',true));
 const key=String(req.headers?.['idempotency-key']||'');if(!IDEM.test(key))return send(res,400,publicError('INVALID_REQUEST','A scoped Idempotency-Key is required'));
 const workflow=WORKFLOWS[req.body.workflow.slug];const requestHash=hash(stable(req.body));const timestamp=now();const row={run_id:`run_${crypto.randomUUID().replaceAll('-','')}`,user_id:identity.userId,request_hash:requestHash,slug:workflow.manifest.slug,workflow_version:workflow.manifest.workflow_version,cost_cents:workflow.costCents,execution_status:'claimed',billing_status:'unbilled',input:req.body.input,created_at:timestamp,updated_at:timestamp,attempt_count:0,artifacts:[]};
 const claim=await store.claim(identity.userId,key,requestHash,row);
 if(!claim.created){if(claim.row.request_hash!==requestHash)return send(res,409,publicError('IDEMPOTENCY_CONFLICT','Idempotency key was already used for another request'));return send(res,202,claim.row.accepted_response||runResource(claim.row))}
 const active=claim.row;
 if(!await store.reserve(identity.userId,workflow.costCents,active.run_id)){await store.paymentFailed(active,{code:'PAYMENT_REQUIRED',message:'Insufficient balance',retryable:false,issues:[]});return send(res,402,runResource(active))}
 await store.markQueued(active);
 const accepted=runResource(active);
 await dispatchRun(store,active,env,fetchImpl);
 return send(res,202,accepted);
}
export { validatePublicBody };
export default async function handler(req,res){return handleRun(req,res)}
