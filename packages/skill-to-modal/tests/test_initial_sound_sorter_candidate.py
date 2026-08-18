"""Candidate-contract tests for the initial sound sorter bundle."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[3]
COMPILER_PATH = ROOT / "packages" / "skill-to-modal" / "compiler.py"
PROFILE_PATH = ROOT / "packages" / "skill-to-modal" / "profiles" / "initial-sound-sorter.json"
SKILL_PATH = ROOT / "containers" / "initial-sound-sorter" / "source" / "SKILL.md"


def _load_compiler():
    spec = importlib.util.spec_from_file_location(
        "initial_sound_sorter_candidate_compiler", COMPILER_PATH
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


COMPILER = _load_compiler()


def _profile() -> dict:
    return json.loads(PROFILE_PATH.read_text(encoding="utf-8"))


def _compiled_files() -> dict[str, str | bytes]:
    profile = _profile()
    return COMPILER.build_files(SKILL_PATH.read_text(encoding="utf-8"), profile)


def test_candidate_compiles_with_only_bounded_words_input() -> None:
    files = _compiled_files()
    input_schema = json.loads(files["schemas/input.json"])

    assert input_schema["required"] == ["words"]
    assert input_schema["additionalProperties"] is False
    assert set(input_schema["properties"]) == {"words"}
    words = input_schema["properties"]["words"]
    assert words["type"] == "array"
    assert words["minItems"] == 1
    assert words["maxItems"] == 24
    assert words["uniqueItems"] is True
    assert words["items"]["minLength"] == 1
    assert words["items"]["maxLength"] == 40
    assert words["items"]["pattern"] == "^[A-Za-z]+(?:['-][A-Za-z]+)*$"


def test_candidate_uses_grouped_warnings_and_usage_contract() -> None:
    files = _compiled_files()
    profile = _profile()
    output_schema = json.loads(files["schemas/output.json"])
    model_schema = profile["live"]["model_output_schema"]
    fixture = profile["happy_path"]["output"]

    Draft202012Validator.check_schema(output_schema)
    Draft202012Validator.check_schema(model_schema)
    assert set(output_schema["required"]) == {
        "run_id",
        "status",
        "workflow_version",
        "grouped",
        "warnings",
        "usage",
    }
    assert model_schema["required"] == ["grouped", "warnings"]
    Draft202012Validator(output_schema).validate(fixture)
    Draft202012Validator(model_schema).validate(
        {"grouped": fixture["grouped"], "warnings": fixture["warnings"]}
    )

    flattened = [word for group in fixture["grouped"] for word in group["items"]]
    assert flattened == profile["happy_path"]["input"]["words"]
    assert len(flattened) == len(set(flattened))
    assert fixture["warnings"] == []


def test_candidate_skill_and_prompt_keep_the_workflow_bounded() -> None:
    skill = SKILL_PATH.read_text(encoding="utf-8")
    profile = _profile()
    prompt = profile["prompts"]["run.txt"]

    assert "required `words` textarea" in skill
    assert "Every input word" in skill
    assert "exactly once" in prompt
    assert "Return exactly the declared JSON fields" in prompt
    assert "instructions" in prompt.lower()
