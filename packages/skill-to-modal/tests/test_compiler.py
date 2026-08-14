"""Unit tests for deterministic, data-only SKILL.md compilation."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[3]
COMPILER_PATH = ROOT / "packages" / "skill-to-modal" / "compiler.py"


def load_compiler():
    spec = importlib.util.spec_from_file_location("skill_to_modal_compiler_test", COMPILER_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


compiler = load_compiler()
SKILL_PATH = ROOT / "packages" / "facebook-ads-copywriter" / "SKILL.md"
PROFILE_PATH = ROOT / "packages" / "skill-to-modal" / "profiles" / "facebook-ads-copywriter.json"


def test_parse_skill_requires_and_returns_frontmatter() -> None:
    parsed = compiler.parse_skill(SKILL_PATH.read_text(encoding="utf-8"))
    assert parsed["name"] == "facebook-ads-copywriter"
    assert parsed["slug"] == "facebook-ads-copywriter"
    assert parsed["description"].startswith("Turn verified product facts")


def test_workflow_steps_are_extracted_in_source_order() -> None:
    parsed = compiler.parse_skill(SKILL_PATH.read_text(encoding="utf-8"))
    assert [step["id"] for step in parsed["extracted_steps"]] == [
        "read-the-brief",
        "choose-angles",
        "write-ads",
        "check-claims",
        "plan-the-test",
    ]


@pytest.mark.parametrize(
    "text,message",
    [
        ("# no frontmatter\n", "must begin"),
        ("---\nname: example\n---\n", "requires name and description"),
        ("---\nname: example\ndescription: open\n", "not closed"),
    ],
)
def test_invalid_skill_metadata_fails_closed(text: str, message: str) -> None:
    with pytest.raises(ValueError, match=message):
        compiler.parse_skill(text)


def test_provider_need_detection_is_stable_and_sorted() -> None:
    needs = compiler.detect_needs("Use ffmpeg, Runware, and faster-whisper. Then ffprobe.")
    assert needs == ["faster-whisper", "ffmpeg", "runware"]


def test_generation_is_byte_deterministic() -> None:
    skill = SKILL_PATH.read_text(encoding="utf-8")
    profile = json.loads(PROFILE_PATH.read_text(encoding="utf-8"))
    first = compiler.build_files(skill, profile)
    second = compiler.build_files(skill, profile)
    assert first == second
    assert first["source/SKILL.md"] == skill
    assert json.loads(first["manifest.json"])["readiness"]["can_submit"] is True


def test_live_metering_rates_come_from_canonical_cost_model() -> None:
    skill = SKILL_PATH.read_text(encoding="utf-8")
    profile = json.loads(PROFILE_PATH.read_text(encoding="utf-8"))
    profile["live"]["input_rate_per_million_usd"] = 99
    profile["live"]["output_rate_per_million_usd"] = 99
    modal_app = compiler.build_files(skill, profile)["modal_app.py"]
    assert "LIVE_INPUT_RATE_PER_MILLION = 0.14" in modal_app
    assert "LIVE_OUTPUT_RATE_PER_MILLION = 0.42" in modal_app


def test_generation_preserves_source_without_a_final_newline() -> None:
    skill = SKILL_PATH.read_text(encoding="utf-8").rstrip("\n")
    profile = json.loads(PROFILE_PATH.read_text(encoding="utf-8"))
    files = compiler.build_files(skill, profile)
    assert files["source/SKILL.md"] == skill
    assert json.loads(files["skill-analysis.json"])["source"]["sha256"] == compiler.sha256_text(skill)


def _generated_runtime(tmp_path: Path):
    skill = (ROOT / "containers" / "phoneme-counter" / "source" / "SKILL.md").read_text(encoding="utf-8")
    profile = json.loads(
        (ROOT / "packages" / "skill-to-modal" / "profiles" / "phoneme-counter.json").read_text(
            encoding="utf-8"
        )
    )
    files = compiler.build_files(skill, profile)
    assert compiler.write_or_check(files, tmp_path, check=False) == 0
    spec = importlib.util.spec_from_file_location("generated_phoneme_counter", tmp_path / "modal_app.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module, profile


def test_generated_repair_is_schema_driven_and_wrapper_allows_one_retry(tmp_path: Path) -> None:
    runtime, profile = _generated_runtime(tmp_path)
    generated = {
        "word": "ship",
        "dialect": "en-US",
        "phonemes": "ʃ,ɪ,p",
        "count": "3",
        "ipa": None,
        "uncertainty": "low",
        "invented": "drop me",
    }
    repaired = runtime._repair_to_schema(
        generated,
        runtime.LIVE_MODEL_OUTPUT_SCHEMA,
        {"word": "ship", "dialect": "en-US", "show_transcription": True},
    )
    assert repaired == {
        "word": "ship",
        "dialect": "en-US",
        "phonemes": ["ʃ", "ɪ", "p"],
        "phoneme_count": 3,
        "ipa": "",
        "uncertainty": "low",
    }
    assert runtime._validation_diff(repaired, runtime.LIVE_MODEL_OUTPUT_SCHEMA) == ""
    sensitive_extra = "RAW_USER_DATA_SENTINEL"
    extra_diff = runtime._validation_diff(
        {**repaired, sensitive_extra: "provider-controlled value"},
        runtime.LIVE_MODEL_OUTPUT_SCHEMA,
    )
    assert "additionalProperties(count=1)" in extra_diff
    assert sensitive_extra not in extra_diff
    assert "provider-controlled value" not in extra_diff
    wrapper = json.loads(compiler.build_files(
        (ROOT / "containers" / "phoneme-counter" / "source" / "SKILL.md").read_text(encoding="utf-8"),
        profile,
    )["schemas/output.json"])
    assert wrapper["properties"]["usage"]["properties"]["llm_calls"] == {
        "type": "integer",
        "minimum": 1,
        "maximum": 2,
    }
    assert "timeout=270" in compiler.build_files(
        (ROOT / "containers" / "phoneme-counter" / "source" / "SKILL.md").read_text(encoding="utf-8"),
        profile,
    )["modal_app.py"]


def test_generated_runtime_retries_once_with_diff_and_aggregates_usage(
    monkeypatch, tmp_path: Path
) -> None:
    runtime, _profile = _generated_runtime(tmp_path)
    for name, value in {
        "LLM_API_KEY": "SECRET_SENTINEL",
        "LLM_BASE_URL": "https://provider.example/v1",
        "LLM_MODEL": "deepseek-v4-flash",
    }.items():
        monkeypatch.setenv(name, value)
    envelopes = [
        {
            "choices": [{"message": {"content": json.dumps({"phonemes": []})}}],
            "usage": {"prompt_tokens": 11, "completion_tokens": 3},
            "model": "deepseek-v4-flash",
        },
        {
            "choices": [{"message": {"content": json.dumps({
                "word": "ship",
                "dialect": "en-US",
                "phonemes": ["ʃ", "ɪ", "p"],
                "phoneme_count": 3,
                "ipa": "ʃɪp",
                "uncertainty": "Low uncertainty for this common word.",
            })}}],
            "usage": {"prompt_tokens": 17, "completion_tokens": 9},
            "model": "deepseek-v4-flash",
        },
    ]
    requests = []

    class Response:
        def __init__(self, value):
            self.value = value
        def __enter__(self):
            return self
        def __exit__(self, exc_type, exc, traceback):
            return False
        def read(self, _limit):
            return json.dumps(self.value).encode("utf-8")

    def fake_urlopen(request, timeout):
        requests.append((json.loads(request.data), timeout))
        return Response(envelopes[len(requests) - 1])

    monkeypatch.setattr(runtime.urllib.request, "urlopen", fake_urlopen)
    result = runtime.execute_workflow({"word": "ship", "dialect": "en-US", "show_transcription": True})
    assert len(requests) == 2
    assert requests[0][0]["response_format"] == {"type": "json_object"}
    assert "json_schema" not in requests[0][0]
    assert "OUTPUT CONTRACT (mandatory)" in requests[0][0]["messages"][0]["content"]
    schema_contract = json.dumps(
        runtime.LIVE_MODEL_OUTPUT_SCHEMA,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    assert schema_contract in requests[0][0]["messages"][0]["content"]
    correction = requests[1][0]["messages"][-1]["content"]
    assert "$.phonemes:minItems(expected=1)" in correction
    assert "SECRET_SENTINEL" not in json.dumps(requests)
    assert result["phoneme_count"] == 3
    assert result["usage"]["llm_calls"] == 2
    assert result["usage"]["prompt_tokens"] == 28
    assert result["usage"]["completion_tokens"] == 12


def test_profile_cannot_change_source_identity() -> None:
    skill = SKILL_PATH.read_text(encoding="utf-8")
    profile = json.loads(PROFILE_PATH.read_text(encoding="utf-8"))
    profile["slug"] = "different-skill"
    with pytest.raises(ValueError, match="does not match skill"):
        compiler.build_files(skill, profile)


def test_nonallowlisted_ready_runtime_is_rejected() -> None:
    skill = SKILL_PATH.read_text(encoding="utf-8")
    profile = json.loads(PROFILE_PATH.read_text(encoding="utf-8"))
    profile["execution_kind"] = "arbitrary_shell"
    with pytest.raises(ValueError, match="non-allowlisted"):
        compiler.build_files(skill, profile)


def test_check_mode_reports_drift_without_writing(tmp_path: Path) -> None:
    files = {"one.txt": "reviewed\n", "nested/two.txt": "stable\n"}
    assert compiler.write_or_check(files, tmp_path, check=True) == 1
    assert list(tmp_path.iterdir()) == []
    assert compiler.write_or_check(files, tmp_path, check=False) == 0
    assert compiler.write_or_check(files, tmp_path, check=True) == 0
