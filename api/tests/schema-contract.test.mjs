import assert from 'node:assert/strict';
import fs from 'node:fs';
import test from 'node:test';

const sql=fs.readFileSync(new URL('../../site/deploy/schema.sql',import.meta.url),'utf8');

test('Postgres schema upgrade contract adds async columns and replaces legacy execution constraint',()=>{
 const fresh=/CREATE TABLE IF NOT EXISTS run_requests\s*\(([\s\S]*?)\n\);/.exec(sql)?.[1]||'';
 for(const status of ['claimed','queued','dispatching','submitted','succeeded','failed'])assert.ok(fresh.includes(`'${status}'`),`fresh constraint lacks ${status}`);
 for(const column of ['response_json TEXT','next_attempt_at TEXT']){
  assert.ok(fresh.replace(/\s+/g,' ').includes(column),`fresh table lacks ${column}`);
  assert.match(sql,new RegExp(`ALTER TABLE run_requests ADD COLUMN IF NOT EXISTS ${column.replace(' ','\\s+')}`));
 }
 const block=/DO \$\$([\s\S]*?)END \$\$;/.exec(sql)?.[1]||'';
 assert.match(block,/pg_constraint/);assert.match(block,/DROP CONSTRAINT %I/);assert.match(block,/ADD CONSTRAINT run_requests_execution_status_check/);
 assert.ok(block.indexOf('DROP CONSTRAINT')<block.indexOf('ADD CONSTRAINT'),'replacement must drop before add');
 for(const status of ['claimed','queued','dispatching','submitted','succeeded','failed'])assert.ok(block.includes(`'${status}'`),`replacement constraint lacks ${status}`);
});