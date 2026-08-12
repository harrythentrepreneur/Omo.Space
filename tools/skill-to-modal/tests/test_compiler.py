import json
import importlib.util
import subprocess
import sys
import types
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]; CLI=ROOT/'tools/skill-to-modal/compiler.py'; SKILL=ROOT/'packages/ugc-script-studio/SKILL.md'
def run(*args): return subprocess.run([sys.executable,str(CLI),*map(str,args)],text=True,capture_output=True)
def skill(tmp, schema, runtime='single-llm'):
 p=tmp/'SKILL.md'; p.write_text(f'''---\nname: test-skill\nversion: 1.2.3\nmetadata:\n  bench:\n    id: test-skill\n    input_schema:\n{schema[0]}    output_schema:\n{schema[1]}    runtime:\n      class: {runtime}\n      provider: openai-compatible\n      operation: chat_json\n      model: test-model\n      adapter: modal-single-llm-v1\n      network: opencode.ai\n---\n# Test\n'''); return p

def test_compiles_complete_runtime_package_deterministically(tmp_path):
 outputs=[]
 for name in ['first','second']:
  out=tmp_path/name; result=run(SKILL,'--output',out); assert result.returncode==0,result.stderr; outputs.append((out,json.loads(result.stdout)))
 expected=['capability-manifest.json','schemas/input.json','schemas/output.json','prompts/system.txt','modal_app.py','container.yaml','README.md','tests/test_contract.py']
 for rel in expected: assert (outputs[0][0]/rel).read_bytes()==(outputs[1][0]/rel).read_bytes()
 result=outputs[0][1]; manifest=json.loads((outputs[0][0]/'capability-manifest.json').read_text())
 assert result['runtime_version']==manifest['runtime_version']; assert result['runtime_version'].startswith('sha256:'); assert len(result['runtime_version'])==71
 assert result['estimated_cost_usd']==manifest['estimated_cost_usd']==0.003
 assert manifest['runtime_class']=='single-llm'; assert manifest['workflow_version']=='1.0.0'
 schema=json.loads((outputs[0][0]/'schemas/input.json').read_text()); assert schema['required']==['product_url','brand_voice','length']; assert schema['additionalProperties'] is False
 modal_app=(outputs[0][0]/'modal_app.py').read_text()
 assert 'modal.App' in modal_app and '@modal.asgi_app(requires_proxy_auth=True)' in modal_app
 assert 'def execute(payload' in modal_app and 'Draft202012Validator' in modal_app

def test_generated_runtime_imports_and_executes_with_stubbed_provider(tmp_path, monkeypatch):
 out=tmp_path/'out'; result=run(SKILL,'--output',out); assert result.returncode==0,result.stdout
 class FakeValidator:
  @staticmethod
  def check_schema(value): return None
  def __init__(self, schema): self.schema=schema
  def validate(self, value):
   if self.schema.get('additionalProperties') is False:
    extra=set(value)-set(self.schema.get('properties',{}))
    if extra: raise ValueError('extra')
 class FakeImage:
  @staticmethod
  def debian_slim(**kwargs): return FakeImage()
  def uv_pip_install(self,*args): return self
  def add_local_dir(self,*args,**kwargs): return self
 class FakeApp:
  def __init__(self,*args,**kwargs): pass
  def function(self,**kwargs):
   def decorate(fn): return fn
   return decorate
 fake_modal=types.SimpleNamespace(Image=FakeImage,App=FakeApp,Secret=types.SimpleNamespace(from_name=lambda name:name),asgi_app=lambda **kwargs: (lambda fn: fn))
 monkeypatch.setitem(sys.modules,'modal',fake_modal)
 monkeypatch.setitem(sys.modules,'jsonschema',types.SimpleNamespace(Draft202012Validator=FakeValidator,ValidationError=ValueError))
 spec=importlib.util.spec_from_file_location('generated_modal_app',out/'modal_app.py')
 module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
 class Chat:
  class completions:
   @staticmethod
   def create(**kwargs):
    content=json.dumps({'hook':'h','shots':['s'],'captions':['c'],'cta':'go'})
    return types.SimpleNamespace(choices=[types.SimpleNamespace(message=types.SimpleNamespace(content=content))])
 client=types.SimpleNamespace(chat=Chat())
 assert module.execute({'product_url':'https://example.com','brand_voice':'raw','length':30},client)['status']=='completed'

def test_supports_declared_optional_fields(tmp_path):
 p=skill(tmp_path,('      required_name: string\n      maybe_note?: string\n','      answer: string\n      detail?: string\n'))
 out=tmp_path/'out'; result=run(p,'--output',out); assert result.returncode==0,result.stdout
 assert json.loads((out/'schemas/input.json').read_text())['required']==['required_name']
 assert json.loads((out/'schemas/output.json').read_text())['required']==['answer']

def test_refuses_unknown_malformed_and_unsupported_types_with_stable_codes(tmp_path):
 cases=[('      x: mystery\n','unknown_field_type'),('      broken line\n','malformed_schema_line'),('      x: array[number]\n','unsupported_array_type'),('      x: enum [one, 2]\n','mixed_enum_types'),('      x: enum []\n','malformed_enum')]
 for i,(line,reason) in enumerate(cases):
  d=tmp_path/str(i);d.mkdir();p=skill(d,(line,'      answer: string\n')); out=d/'out'; result=run(p,'--output',out); body=json.loads(result.stdout)
  assert result.returncode==2; assert reason in body['reasons']; assert body['reasons']==sorted(set(body['reasons'])); assert not out.exists()

def test_refuses_unsupported_or_undeclared_runtime_class_adapter_provider_operation_model_and_network(tmp_path):
 for i,(runtime,adapter,reason) in enumerate([('gpu','modal-single-llm-v1','unsupported_runtime_class'),('single-llm','browser-worker','unsupported_runtime_adapter'),('', 'modal-single-llm-v1','missing_runtime_class')]):
  d=tmp_path/str(i);d.mkdir(); p=skill(d,('      x: string\n','      answer: string\n'),runtime or 'MISSING')
  text=p.read_text().replace('class: MISSING\n','').replace('adapter: modal-single-llm-v1',f'adapter: {adapter}');p.write_text(text)
  result=run(p,'--output',d/'out'); assert reason in json.loads(result.stdout)['reasons']; assert result.returncode==2
 for i,(needle,reason) in enumerate([('      model: test-model\n','missing_runtime_model'),('      provider: openai-compatible\n','missing_runtime_provider'),('      operation: chat_json\n','missing_runtime_operation'),('      network: opencode.ai\n','missing_runtime_network')]):
  d=tmp_path/f'explicit{i}';d.mkdir();p=skill(d,('      x: string\n','      answer: string\n'))
  p.write_text(p.read_text().replace(needle,''))
  result=run(p,'--output',d/'out'); assert result.returncode==2; assert reason in json.loads(result.stdout)['reasons']

def test_refuses_malformed_frontmatter_missing_version_and_undeclared_capability_fields(tmp_path):
 cases=[('not yaml','malformed_frontmatter'),('''---\nname: x\nmetadata:\n  bench:\n    id: x\n    input_schema:\n      x: string\n    output_schema:\n      y: string\n    runtime:\n      class: single-llm\n      provider: openai-compatible\n      operation: chat_json\n      adapter: modal-single-llm-v1\n      network: opencode.ai\n---\n''','missing_workflow_version'),(SKILL.read_text().replace('      network: opencode.ai\n','      network: opencode.ai\n      browser: chromium\n'),'unsupported_runtime_declaration')]
 for i,(text,reason) in enumerate(cases):
  p=tmp_path/f'{i}.md';p.write_text(text); result=run(p,'--output',tmp_path/f'out{i}'); assert result.returncode==2; assert reason in json.loads(result.stdout)['reasons']

def test_refusal_never_creates_partial_output_and_never_emits_secret_values(tmp_path,monkeypatch):
 monkeypatch.setenv('LLM_API_KEY','DO_NOT_LEAK_123'); out=tmp_path/'out'; result=run(SKILL,'--output',out); combined=result.stdout+''.join(p.read_text() for p in out.rglob('*') if p.is_file()); assert 'DO_NOT_LEAK_123' not in combined
 bad=tmp_path/'bad.md';bad.write_text('---\nname: bad\n---\n'); badout=tmp_path/'badout'; result=run(bad,'--output',badout); assert result.returncode==2 and not badout.exists()
