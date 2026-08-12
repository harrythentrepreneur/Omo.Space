import json
from pathlib import Path
ROOT=Path(__file__).parents[1]
def test_schemas_are_closed():
    for name in ("input.json","output.json"):
        assert json.loads((ROOT/"schemas"/name).read_text())["additionalProperties"] is False
