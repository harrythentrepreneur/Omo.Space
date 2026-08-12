#!/usr/bin/env python3
"""Fail-closed compiler for the constrained Cognition single-LLM runtime."""
import argparse, hashlib, json, re, shutil, sys, tempfile
from pathlib import Path

TYPE_MAP={"string":{"type":"string","minLength":1,"maxLength":2000},"number":{"type":"number"},"boolean":{"type":"boolean"}}
ALLOWED_RUNTIME_CLASSES={"single-llm"}
ALLOWED_ADAPTERS={"bench-cloudflare-workers","modal-single-llm-v1"}
ALLOWED_PROVIDERS={"openai-compatible"}
ALLOWED_OPERATIONS={"chat_json"}
ALLOWED_NETWORKS={"opencode.ai","api.openai.com"}

def refuse(*reasons): return {"status":"unsupported","reasons":sorted(set(reasons)),"manual_actions":[]},2

def parse(text):
 if not text.startswith('---\n') or '\n---\n' not in text[4:]: return None,None,'malformed_frontmatter'
 raw,body=text[4:].split('\n---\n',1); data={}; bench={}; runtime={}; schemas={}; section=[]
 for line in raw.splitlines():
  if not line.strip() or line.lstrip().startswith('#'): continue
  indent=len(line)-len(line.lstrip()); m=re.fullmatch(r'([A-Za-z_][A-Za-z0-9_-]*\??):(?:\s*(.*))?',line.strip())
  if not m:
   if indent==6 and len(section)==2 and section[1] in ('input_schema','output_schema'):
    return {'parse_reason':'malformed_schema_line'},body,None
   return None,None,'malformed_frontmatter'
  key,val=m.groups(); val=(val or '').strip().strip('"')
  if indent==0: data[key]=val; section=[]
  elif indent==2 and key=='bench': section=['bench']
  elif indent==4 and section[:1]==['bench']:
   bench[key]=val;section=['bench',key] if not val else ['bench']
  elif indent==6 and len(section)==2 and section[1] in ('input_schema','output_schema'): schemas.setdefault(section[1],[]).append((key,val))
  elif indent==6 and len(section)==2 and section[1]=='runtime': runtime[key]=val
 return {**data,**bench,'runtime':runtime,'schemas':schemas},body,None

def schema(fields,label):
 if fields is None:return None,[f'missing_{label}']
 props={};required=[];reasons=[]
 for raw_key,value in fields:
  optional=raw_key.endswith('?');key=raw_key[:-1] if optional else raw_key
  if not key or key in props:reasons.append('malformed_schema_line');continue
  enum=re.fullmatch(r'enum\s*\[(.*)\]',value)
  if value.startswith('enum'):
   if not enum or not enum.group(1).strip():reasons.append('malformed_enum');continue
   vals=[]
   for token in enum.group(1).split(','):
    token=token.strip().strip('"').strip("'")
    if re.fullmatch(r'-?\d+',token):vals.append(int(token))
    elif token:vals.append(token)
    else:reasons.append('malformed_enum')
   if len({type(x) for x in vals})!=1:reasons.append('mixed_enum_types');continue
   props[key]={'type':'integer' if isinstance(vals[0],int) else 'string','enum':vals}
  elif value.startswith('array['):
   if value!='array[string]':reasons.append('unsupported_array_type');continue
   props[key]={'type':'array','items':{'type':'string'},'minItems':1,'maxItems':20}
  elif value in TYPE_MAP:props[key]=dict(TYPE_MAP[value])
  else:reasons.append('unknown_field_type');continue
  if not optional:required.append(key)
 return {'$schema':'https://json-schema.org/draft/2020-12/schema','type':'object','properties':props,'required':required,'additionalProperties':False},reasons

def dump(value):return json.dumps(value,indent=2,sort_keys=True)+'\n'
def runtime_files(slug,model):
 return {
 'modal_app.py':f'''"""Generated deterministic Modal single-LLM runtime. Do not edit; regenerate."""
import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Any

import modal
from jsonschema import Draft202012Validator

APP_NAME = "cognition-{slug}"
ROOT = Path(__file__).parent
IMAGE_ROOT = Path("/root/{slug}")
DEFAULT_MODEL = {model!r}

def assets() -> Path:
    return ROOT if (ROOT / "schemas/input.json").exists() else IMAGE_ROOT

@lru_cache(None)
def schema(name: str) -> dict[str, Any]:
    value = json.loads((assets() / "schemas" / name).read_text())
    Draft202012Validator.check_schema(value)
    return value

def validate(value: Any, name: str) -> None:
    Draft202012Validator(schema(name)).validate(value)

def parse_output(raw: str) -> dict[str, Any]:
    if not isinstance(raw, str):
        raise ValueError("invalid provider JSON")
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        first = cleaned.find("\\n")
        last = cleaned.rfind("```")
        if first >= 0 and last > first:
            cleaned = cleaned[first + 1:last].strip()
    start = cleaned.find("{{")
    if start < 0:
        raise ValueError("invalid provider JSON")
    try:
        value, end = json.JSONDecoder().raw_decode(cleaned[start:])
    except (TypeError, json.JSONDecodeError) as exc:
        raise ValueError("invalid provider JSON") from exc
    if cleaned[start + end:].strip():
        raise ValueError("invalid provider JSON")
    validate(value, "output.json")
    return value

def execute(payload: dict[str, Any], client: Any = None) -> dict[str, Any]:
    validate(payload, "input.json")
    if client is None:
        from openai import OpenAI
        provider_key = os.environ.get("LLM_API_KEY") or os.environ.get("OPENCODE_GO_API_KEY")
        if not provider_key:
            raise KeyError("LLM_API_KEY")
        client = OpenAI(api_key=provider_key, base_url=os.environ.get("LLM_BASE_URL", "https://opencode.ai/zen/go/v1"))
    prompt = (assets() / "prompts/system.txt").read_text()
    response = client.chat.completions.create(
        model=os.environ.get("LLM_MODEL", DEFAULT_MODEL),
        temperature=0.3,
        max_tokens=900,
        response_format={{"type": "json_object"}},
        messages=[
            {{"role": "system", "content": prompt + "\\nReturn only one JSON object, without markdown fences or commentary."}},
            {{"role": "user", "content": json.dumps(payload, sort_keys=True)}},
        ],
    )
    return {{"status": "completed", "result": parse_output(response.choices[0].message.content), "usage": {{"estimated_cost_usd": 0.001}}}}

def create_app(client: Any = None):
    from fastapi import FastAPI, HTTPException
    from jsonschema import ValidationError
    web = FastAPI(title="Cognition {slug}", version="1.0.0")

    @web.get("/health")
    def health() -> dict[str, Any]:
        return {{"ok": True, "workflow": {slug!r}}}

    @web.post("/v1/run")
    def run(body: Any) -> dict[str, Any]:
        try:
            return execute(body, client)
        except ValidationError as exc:
            raise HTTPException(422, "Input does not match workflow schema") from exc
        except (ValueError, KeyError, IndexError, TypeError) as exc:
            raise HTTPException(502, "Provider returned an invalid response") from exc
    return web

image = (
    modal.Image.debian_slim(python_version="3.12")
    .uv_pip_install("modal==1.5.0", "fastapi==0.109.0", "openai==2.36.0", "jsonschema==4.26.0")
    .add_local_dir(ROOT / "schemas", IMAGE_ROOT / "schemas", copy=True)
    .add_local_dir(ROOT / "prompts", IMAGE_ROOT / "prompts", copy=True)
)
app = modal.App(APP_NAME)
provider_secret = modal.Secret.from_name("omo-keys")

@app.function(image=image, secrets=[provider_secret], cpu=0.25, memory=512, timeout=150)
def canary() -> dict[str, Any]:
    result = execute({{"product_url": "https://example.com/silk-pillowcase", "brand_voice": "honest", "length": 30}})
    print(json.dumps({{"status": result["status"], "result_keys": sorted(result["result"])}}))
    return result

@app.function(image=image, secrets=[provider_secret], cpu=0.25, memory=512, timeout=150, min_containers=0, max_containers=10, scaledown_window=2)
@modal.asgi_app(requires_proxy_auth=True)
def api():
    return create_app()
''',
 'container.yaml':f'''slug: {slug}\nruntime_class: single-llm\nentrypoint: modal_app.py\nproxy_auth_required: true\n''',
 'README.md':f'''# {slug} generated runtime\n\nDeterministically generated by `tools/skill-to-modal/compiler.py`. Regenerate rather than editing generated files. The endpoint must use Modal proxy authentication.\n''',
 'tests/test_contract.py':'''import json\nfrom pathlib import Path\nROOT=Path(__file__).parents[1]\ndef test_schemas_are_closed():\n    for name in ("input.json","output.json"):\n        assert json.loads((ROOT/"schemas"/name).read_text())["additionalProperties"] is False\n'''}

def compile_skill(path,out):
 try:text=path.read_text()
 except Exception:return refuse('skill_unreadable')
 meta,body,error=parse(text)
 if error:return refuse(error)
 reasons=[]
 if meta.get('parse_reason'):return refuse(meta['parse_reason'])
 if not meta.get('version') or not re.fullmatch(r'\d+\.\d+\.\d+',meta.get('version','')):reasons.append('missing_workflow_version')
 inp,r=schema(meta['schemas'].get('input_schema'),'input_schema');reasons+=r
 output,r=schema(meta['schemas'].get('output_schema'),'output_schema');reasons+=r
 runtime=meta['runtime'];runtime_class=runtime.get('class','')
 if not runtime_class:reasons.append('missing_runtime_class')
 elif runtime_class not in ALLOWED_RUNTIME_CLASSES:reasons.append('unsupported_runtime_class')
 if not runtime.get('adapter'):reasons.append('missing_runtime_adapter')
 elif runtime.get('adapter') not in ALLOWED_ADAPTERS:reasons.append('unsupported_runtime_adapter')
 if not runtime.get('provider'):reasons.append('missing_runtime_provider')
 elif runtime.get('provider') not in ALLOWED_PROVIDERS:reasons.append('unsupported_runtime_provider')
 if not runtime.get('operation'):reasons.append('missing_runtime_operation')
 elif runtime.get('operation') not in ALLOWED_OPERATIONS:reasons.append('unsupported_runtime_operation')
 if not runtime.get('network'):reasons.append('missing_runtime_network')
 elif runtime.get('network') not in ALLOWED_NETWORKS:reasons.append('unsupported_runtime_network')
 if not runtime.get('model'):reasons.append('missing_runtime_model')
 extra=sorted(set(runtime)-{'class','adapter','provider','operation','model','network'})
 if extra:reasons.append('unsupported_runtime_declaration')
 if reasons:return refuse(*reasons)
 slug=meta.get('id') or meta.get('name'); model=runtime.get('model','')
 base={'spec_version':'cognition.capability/v1','slug':slug,'workflow_version':meta['version'],'runtime_class':'single-llm','provider':runtime['provider'],'operation':runtime['operation'],'network':runtime['network'],'required_secrets':[{'name':'LLM_API_KEY','purpose':'OpenAI-compatible provider authentication'}],'model':model,'input_schema':'schemas/input.json','output_schema':'schemas/output.json','estimated_cost_usd':0.003}
 prompt=f"You are {meta.get('name',slug)}. Follow this workflow and return only JSON matching the output schema. Never invent product facts.\n\n{body.strip()}\n"
 files={'schemas/input.json':dump(inp),'schemas/output.json':dump(output),'prompts/system.txt':prompt,**runtime_files(slug,model)}
 digest=hashlib.sha256();digest.update(dump(base).encode())
 for name in sorted(files):digest.update(name.encode()+b'\0'+files[name].encode())
 base['runtime_version']='sha256:'+digest.hexdigest();files['capability-manifest.json']=dump(base)
 parent=out.parent;parent.mkdir(parents=True,exist_ok=True);tmp=Path(tempfile.mkdtemp(prefix='.skill-compile-',dir=parent))
 try:
  for name,content in files.items():p=tmp/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(content)
  if out.exists():shutil.rmtree(out)
  tmp.rename(out)
 except Exception:
  shutil.rmtree(tmp,ignore_errors=True);raise
 result={'status':'compiled','slug':slug,'runtime_class':'single-llm','runtime_version':base['runtime_version'],'required_secrets':['LLM_API_KEY'],'input_schema_path':str(out/'schemas/input.json'),'output_schema_path':str(out/'schemas/output.json'),'estimated_cost_usd':base['estimated_cost_usd'],'limitations':['single synchronous OpenAI-compatible LLM call']}
 return result,0

def main():
 p=argparse.ArgumentParser();p.add_argument('skill',type=Path);p.add_argument('--output',type=Path,required=True);a=p.parse_args();result,code=compile_skill(a.skill,a.output);print(json.dumps(result,sort_keys=True));return code
if __name__=='__main__':sys.exit(main())
