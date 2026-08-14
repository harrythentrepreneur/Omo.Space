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


def _generated_runtime_for(tmp_path: Path, slug: str):
    skill = (ROOT / "containers" / slug / "source" / "SKILL.md").read_text(encoding="utf-8")
    profile = json.loads(
        (ROOT / "packages" / "skill-to-modal" / "profiles" / f"{slug}.json").read_text(
            encoding="utf-8"
        )
    )
    files = compiler.build_files(skill, profile)
    output = tmp_path / slug
    assert compiler.write_or_check(files, output, check=False) == 0
    spec = importlib.util.spec_from_file_location(
        "generated_" + slug.replace("-", "_"), output / "modal_app.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module, profile


def _generated_runtime(tmp_path: Path):
    return _generated_runtime_for(tmp_path, "phoneme-counter")


def _model_fixture(profile: dict) -> dict:
    output = profile["happy_path"]["output"]
    return {
        name: json.loads(json.dumps(output[name]))
        for name in profile["live"]["model_output_schema"]["properties"]
        if name in output
    }


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


def test_generated_digraph_normalizer_derives_exact_absolute_source_occurrences(
    tmp_path: Path,
) -> None:
    runtime, _profile = _generated_runtime_for(tmp_path, "digraph-spotter")
    payload = {
        "text": "The chick and the sheep sat by the shed.",
        "digraph_type": "consonant",
        "include_explanations": True,
        "dialect": "en-US",
    }
    provider_value = {
        "occurrences": [
            {
                "text": "ch",
                "word": "chick",
                "start": 4,
                "end": 6,
                "type": "consonant",
                "explanation": "Provider prose for the exact occurrence.",
            },
            {
                "text": "ch",
                "word": "sheep",
                "start": 16,
                "end": 18,
                "type": "consonant",
                "explanation": "Provider prose for a bad span.",
            },
        ],
        "summary": ["ch"],
        "warnings": [],
    }
    normalized, diff = runtime._candidate(json.dumps(provider_value), payload)
    assert diff == ""
    assert normalized is not None
    assert [
        (item["text"], item["word"], item["start"], item["end"], item["type"])
        for item in normalized["occurrences"]
    ] == [
        ("Th", "The", 0, 2, "consonant"),
        ("ch", "chick", 4, 6, "consonant"),
        ("ck", "chick", 7, 9, "consonant"),
        ("th", "the", 14, 16, "consonant"),
        ("sh", "sheep", 18, 20, "consonant"),
        ("th", "the", 31, 33, "consonant"),
        ("sh", "shed", 35, 37, "consonant"),
    ]
    assert normalized["summary"] == ["th", "ch", "ck", "sh"]
    assert normalized["occurrences"][1]["explanation"] == "Provider prose for the exact occurrence."
    assert "explanation" not in normalized["occurrences"][4]
    broken = json.loads(json.dumps(normalized))
    broken["occurrences"][0]["start"] = 1
    assert "semantic_source_spans" in runtime._semantic_validation_diff(broken, payload)


@pytest.mark.parametrize(
    "slug,flag,path",
    [
        ("phoneme-counter", "show_transcription", ("ipa",)),
        (
            "decodable-sentence-creator",
            "include_sight_words",
            ("sentences", 0, "sight_or_irregular_words"),
        ),
        (
            "digraph-spotter",
            "include_explanations",
            ("occurrences", 0, "explanation"),
        ),
        (
            "grapheme-to-phoneme-converter",
            "include_rules_explanation",
            ("rules_explanation",),
        ),
    ],
)
def test_false_flags_remove_optional_fields_instead_of_emptying_them(
    tmp_path: Path, slug: str, flag: str, path: tuple[str | int, ...]
) -> None:
    runtime, profile = _generated_runtime_for(tmp_path, slug)
    payload = json.loads(json.dumps(profile["happy_path"]["input"]))
    payload[flag] = False
    normalized, diff = runtime._candidate(json.dumps(_model_fixture(profile)), payload)
    assert diff == ""
    assert normalized is not None
    parent = normalized
    for part in path[:-1]:
        parent = parent[part]
    assert path[-1] not in parent

    wrapper = compiler.runtime_output_schema(profile)
    current = wrapper
    configured_path = profile["semantic_normalizers"]["flag_fields"][0]["path"]
    for part in configured_path[:-1]:
        current = current["items"] if part == "*" else current["properties"][part]
    assert configured_path[-1] not in current.get("required", [])


def test_phoneme_containment_drops_invalid_words_and_reports_safe_semantic_count(
    tmp_path: Path,
) -> None:
    runtime, _profile = _generated_runtime_for(tmp_path, "phonics-list-generator")
    payload = {
        "phonemes": ["ai", "ay"],
        "topic": "outdoor play",
        "difficulty_level": "intermediate",
        "dialect": "en-GB",
        "word_count": 5,
    }

    def item(word: str, claimed: str) -> dict:
        return {
            "word": word,
            "matched_phonemes": [claimed],
            "target_position": "medial",
            "pronunciation_note": "Review pronunciation in the selected dialect.",
        }

    provider_value = {
        "words": [
            item("play", "ay"),
            item("rain", "ai"),
            item("swing", "ai"),
            item("slide", "ai"),
            item("clay", "ay"),
            item("paint", "ai"),
            item("trail", "ai"),
        ],
        "coverage": ["ai", "ay"],
        "warnings": [],
    }
    normalized, diff = runtime._candidate(json.dumps(provider_value), payload)
    assert diff == ""
    assert normalized is not None
    assert [entry["word"] for entry in normalized["words"]] == [
        "play",
        "rain",
        "clay",
        "paint",
        "trail",
    ]
    assert normalized["coverage"] == ["ai", "ay"]
    assert normalized["words"][0]["matched_phonemes"] == ["ay"]
    assert normalized["words"][0]["target_position"] == "final"
    assert normalized["warnings"][-1].startswith("Removed 2 words")

    retry_payload = {**payload, "word_count": 6}
    _shortened, semantic_diff = runtime._candidate(json.dumps(provider_value), retry_payload)
    assert "semantic_word_count(expected=6,actual=5)" in semantic_diff
    assert "swing" not in semantic_diff
    assert "slide" not in semantic_diff


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
