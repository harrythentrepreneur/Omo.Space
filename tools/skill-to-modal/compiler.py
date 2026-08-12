#!/usr/bin/env python3
"""Fail-closed compiler for the constrained Cognition single-LLM runtime."""
import argparse, hashlib, json, re, shutil, sys, tempfile
from pathlib import Path

TYPE_MAP={"string":{"type":"string","minLength":1,"maxLength":2000},"number":{"type":"number"},"boolean":{"type":"boolean"}}
ALLOWED_RUNTIME_CLASSES={"single-llm","media-sequential","private-document-pipeline"}
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

PRIVATE_REASON_CODES=["APPROVAL_REQUIRED_BEFORE_REAL_DATA","EXTERNAL_SOURCE_REPOSITORY_UNAVAILABLE","FIXTURE_ONLY_DEVELOPMENT_REQUIRED","PRIVATE_DATA_ISOLATION_RETENTION_REQUIRED"]
MEDIA_KEYS={'class','adapter','provider','operation','network','generation_fps','checkpoint_frames','portrait_width','portrait_height','retry_attempts','retry_backoff_seconds'}

def media_runtime_files(slug):
 return {'runtime.py':'''"""Generated fixture-backed async media orchestration contract."""
import asyncio, hashlib, json, math, shutil, struct, subprocess, wave
from pathlib import Path

STAGES=("accept","transcribe","derive","brief","frames","assemble","validate")
RETRY_BACKOFF_SECONDS=(0.01,0.02,0.04)

def _write_ppm(path, width, height, value):
    path.parent.mkdir(parents=True,exist_ok=True)
    pixel=bytes((value%220, value%220, value%220)); path.write_bytes(f"P6\\n{width} {height}\\n255\\n".encode()+pixel*(width*height))
def _size(path):
    with path.open('rb') as f:
        magic=f.readline(); width,height=map(int,f.readline().split())
    return width,height
def _artifact(root,path,kind,media_type):
    return {"kind":kind,"path":str(path.relative_to(root)),"sha256":hashlib.sha256(path.read_bytes()).hexdigest(),"media_type":media_type}

class FakeFrameProvider:
    in_flight=0; max_in_flight=0; events=[]
    def __init__(self,landscape_once=None):
        type(self).in_flight=0; type(self).max_in_flight=0; type(self).events=[]
        self.landscape_once=set(landscape_once or ()); self.attempts={}
    async def generate(self,index,parent,out):
        cls=type(self); cls.in_flight+=1; cls.max_in_flight=max(cls.max_in_flight,cls.in_flight); cls.events.append({"event":"start","frame":index})
        self.attempts[index]=self.attempts.get(index,0)+1
        try:
            await asyncio.sleep(0)
            landscape=index in self.landscape_once and self.attempts[index]==1
            _write_ppm(out,640 if landscape else 360,360 if landscape else 640,30+index*20)
            return out
        finally:
            cls.events.append({"event":"end","frame":index}); cls.in_flight-=1

def _assemble_ffmpeg(root,frames,duration):
    audio=root/'fixture.wav'; video=root/'video.mp4'
    with wave.open(str(audio),'wb') as wav:
        wav.setparams((1,2,8000,0,'NONE','not compressed'))
        samples=b''.join(struct.pack('<h',int(1000*math.sin(2*math.pi*220*i/8000))) for i in range(int(duration*8000)))
        wav.writeframes(samples)
    ffmpeg=shutil.which('ffmpeg')
    if not ffmpeg: return None,audio
    subprocess.run([ffmpeg,'-y','-loglevel','error','-framerate','1','-i',str(root/'frames/F%03d.ppm'),'-i',str(audio),'-t',str(duration),'-r','30','-c:v','libx264','-pix_fmt','yuv420p','-c:a','aac','-movflags','+faststart',str(video)],check=True)
    return video,audio
def _probe(video,expected):
    probe=shutil.which('ffprobe')
    if not probe: return expected
    raw=subprocess.check_output([probe,'-v','error','-show_entries','format=duration','-of','default=nw=1:nk=1',str(video)],text=True)
    actual=float(raw.strip())
    if abs(actual-expected)>0.2: raise ValueError('duration_contract_failed')
    return actual

async def orchestrate(payload,workdir,provider=None,sleep=asyncio.sleep,checkpoint_frames=6):
    if provider is None:
        return {"status":"blocked","code":"PRODUCTION_FRAME_PROVIDER_UNAVAILABLE","retryable":False,"artifacts":[]}
    root=Path(workdir); root.mkdir(parents=True,exist_ok=True); duration=float(payload['duration_seconds']); total=max(1,math.ceil(duration)); progress=[]
    for stage in STAGES[:4]: progress.append({"stage":stage,"state":"completed","completed":0,"total":total})
    frames=root/'frames'; frames.mkdir(exist_ok=True); parent=None
    for index in range(total):
        target=frames/f'F{index:03d}.ppm'
        if target.exists() and _size(target)[0]<_size(target)[1]: parent=target; continue
        for attempt,delay in enumerate(RETRY_BACKOFF_SECONDS):
            await provider.generate(index,parent,target)
            width,height=_size(target)
            if width<height: break
            target.unlink(missing_ok=True)
            if attempt==len(RETRY_BACKOFF_SECONDS)-1: raise ValueError('portrait_orientation_required')
            result=sleep(delay)
            if hasattr(result,'__await__'): await result
        parent=target
        if (index+1)%checkpoint_frames==0:
            cp=root/'checkpoints'/f'checkpoint-{index:06d}.json'; cp.parent.mkdir(exist_ok=True); cp.write_text(json.dumps({"last_frame":index},sort_keys=True)+'\\n')
    progress.append({"stage":"frames","state":"completed","completed":total,"total":total})
    video,audio=_assemble_ffmpeg(root,list(frames.glob('*.ppm')),duration); progress.append({"stage":"assemble","state":"completed","completed":total,"total":total})
    actual=_probe(video,duration) if video else duration
    manifest=root/'run-manifest.json'; manifest.write_text(json.dumps({"duration_seconds":actual,"frame_count":total,"fixture":True},sort_keys=True)+'\\n')
    artifacts=[_artifact(root,audio,'audio','audio/wav'),_artifact(root,manifest,'manifest','application/json')]
    if video: artifacts.insert(0,_artifact(root,video,'video','video/mp4'))
    artifacts += [_artifact(root,p,'frame','image/x-portable-pixmap') for p in sorted(frames.glob('*.ppm'))]
    progress.append({"stage":"validate","state":"completed","completed":total,"total":total})
    return {"status":"completed","duration_seconds":actual,"progress":progress,"artifacts":artifacts}

async def run_fixture(workdir,duration_seconds=3,checkpoint_frames=6):
    return await orchestrate({"audio_ref":"fixture://tone","duration_seconds":duration_seconds},workdir,FakeFrameProvider(),checkpoint_frames=checkpoint_frames)
''',
 'README.md':f'''# {slug} generated runtime\n\nDeterministic fixture-backed proof. `runtime.py` exposes an async orchestration contract. Production image generation is intentionally blocked until an approved server-side provider exists. FFmpeg/ffprobe are used when installed; no provider credentials or private data are included.\n''',
 'tests/test_contract.py':'''import importlib.util\nfrom pathlib import Path\ndef test_contract():\n spec=importlib.util.spec_from_file_location("generated_media_contract_runtime",Path(__file__).parents[1]/"runtime.py")\n runtime=importlib.util.module_from_spec(spec);spec.loader.exec_module(runtime)\n assert runtime.STAGES[-1]=="validate"\n assert runtime.RETRY_BACKOFF_SECONDS==tuple(sorted(runtime.RETRY_BACKOFF_SECONDS))\n'''}

def write_package(out,files,base):
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
 return base['runtime_version']
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
 if runtime_class=='private-document-pipeline':
  expected={'class','adapter','source_repository','data_mode','privacy_isolation','retention_controls','real_data_approval'}
  if set(runtime)!=expected: return refuse('unsupported_runtime_declaration')
  result={"status":"unsupported_with_reason","runtime_class":runtime_class,"reasons":PRIVATE_REASON_CODES,"manual_actions":["provide approved source repository","approve privacy isolation and retention architecture","use fictional fixtures only until approval"]}
  return result,2
 if runtime_class=='media-sequential':
  if set(runtime)!=MEDIA_KEYS:return refuse('unsupported_runtime_declaration')
  expected={'adapter':'fixture-media-sequential-v1','provider':'provider-neutral','operation':'audio_symbolic_animation','network':'none','generation_fps':'1','checkpoint_frames':'6','portrait_width':'360','portrait_height':'640','retry_attempts':'3','retry_backoff_seconds':'0.01'}
  for key,value in expected.items():
   if runtime.get(key)!=value:reasons.append('unsupported_runtime_declaration')
  if reasons:return refuse(*reasons)
  slug=meta.get('id') or meta.get('name')
  base={'spec_version':'cognition.capability/v1','slug':slug,'workflow_version':meta['version'],'runtime_class':runtime_class,'adapter':runtime['adapter'],'provider':'fixture-only','operation':runtime['operation'],'network':'none','required_secrets':[],'input_schema':'schemas/input.json','output_schema':'schemas/output.json','estimated_cost_usd':0,'cost_model':{'fixture':'no external provider cost','production':'unknown until approved provider is integrated'},'limitations':['fixture-only frame provider','production frame provider unavailable','transcription and symbol derivation are deterministic fixture contracts','FFmpeg assembly requires local ffmpeg']}
  files={'schemas/input.json':dump(inp),'schemas/output.json':dump(output),**media_runtime_files(slug)}
  version=write_package(out,files,base)
  return {'status':'compiled','slug':slug,'runtime_class':runtime_class,'runtime_version':version,'required_secrets':[],'input_schema_path':str(out/'schemas/input.json'),'output_schema_path':str(out/'schemas/output.json'),'estimated_cost_usd':0,'limitations':base['limitations']},0
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
