import importlib.util,json
from pathlib import Path
from types import SimpleNamespace
import pytest
from jsonschema import ValidationError
ROOT=Path(__file__).parents[1]/"generated";spec=importlib.util.spec_from_file_location("ugc_runtime",ROOT/"modal_app.py");m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
GOOD={"product_url":"https://example.com/p","brand_voice":"honest","length":30}; OUT={"hook":"I tried it","shots":["Show product"],"captions":["honest take"],"cta":"Try it"}
class C:
 def __init__(self,raw): self.chat=SimpleNamespace(completions=SimpleNamespace(create=lambda **_:SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=raw))])))
def test_executes_stubbed_contract(monkeypatch):
 monkeypatch.delenv("LLM_API_KEY",raising=False); result=m.execute(GOOD,C(json.dumps(OUT)));assert result["result"]==OUT
@pytest.mark.parametrize("bad",[{**GOOD,"extra":1},{**GOOD,"brand_voice":"fake"},{**GOOD,"length":20}])
def test_rejects_invalid_input_before_spend(bad):
 with pytest.raises(ValidationError):m.execute(bad,C(json.dumps(OUT)))
def test_rejects_provider_extra_fields():
 with pytest.raises(ValidationError):m.parse_output(json.dumps({**OUT,"raw":"leak"}))
def test_health_and_run_are_only_routes():
 paths={r.path for r in m.create_app(C(json.dumps(OUT))).routes if not r.path.startswith(("/openapi","/docs","/redoc"))};assert paths=={"/health","/v1/run"}
def test_modal_endpoint_requires_proxy_auth(): assert "requires_proxy_auth=True" in (ROOT/"modal_app.py").read_text()
