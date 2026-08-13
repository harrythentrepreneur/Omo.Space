import { createNeonStore, reconcileRuns } from './v1/runs.js';

export default async function handler(req,res){
 if(req.method!=='GET'&&req.method!=='POST')return res.status(405).json({error:'method_not_allowed'});
 if(!process.env.CRON_SECRET||req.headers.authorization!==`Bearer ${process.env.CRON_SECRET}`)return res.status(401).json({error:'unauthorized'});
 const required=['MODAL_PROXY_TOKEN_ID','MODAL_PROXY_TOKEN_SECRET'];
 if((!process.env.DATABASE_URL&&!process.env.NEON_DATABASE_URL)||required.some(name=>!process.env[name])||(!process.env.MODAL_UGC_ENDPOINT&&!process.env.MODAL_FACEBOOK_ADS_ENDPOINT))return res.status(503).json({error:'server_not_configured'});
 try{
  const store=await createNeonStore(process.env);
  const reconciled=await reconcileRuns(store,process.env,fetch,{limit:20});
  return res.status(200).json({ok:true,reconciled});
 }catch{
  return res.status(503).json({error:'reconcile_unavailable'});
 }
}
