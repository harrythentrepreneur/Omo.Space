import importlib.util
from pathlib import Path
def test_contract():
 spec=importlib.util.spec_from_file_location("generated_media_contract_runtime",Path(__file__).parents[1]/"runtime.py")
 runtime=importlib.util.module_from_spec(spec);spec.loader.exec_module(runtime)
 assert runtime.STAGES[-1]=="validate"
 assert runtime.RETRY_BACKOFF_SECONDS==tuple(sorted(runtime.RETRY_BACKOFF_SECONDS))
