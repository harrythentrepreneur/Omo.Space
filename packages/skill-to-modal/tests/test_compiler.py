"""Unit tests for deterministic, data-only SKILL.md compilation."""

from __future__ import annotations

import importlib.util
import json
import shutil
import subprocess
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


def test_generator_materializes_whatsapp_zip_and_book_pdf_contracts() -> None:
    skill_path = ROOT / "containers" / "woven-storybook-pipeline" / "source" / "SKILL.md"
    profile_path = (
        ROOT / "packages" / "skill-to-modal" / "profiles" / "woven-storybook-pipeline.json"
    )
    profile = json.loads(profile_path.read_text(encoding="utf-8"))
    files = compiler.build_files(skill_path.read_text(encoding="utf-8"), profile)
    input_schema = json.loads(files["schemas/input.json"])
    output_schema = json.loads(files["schemas/output.json"])
    manifest = json.loads(files["manifest.json"])

    assert input_schema["properties"]["chat_zip"]["properties"]["content_base64"]["maxLength"] == 2_666_668
    assert input_schema["oneOf"][0]["required"] == profile["input_adapter_config"]["whatsapp_zip"]["target_fields"]
    assert input_schema["oneOf"][1]["required"] == ["chat_zip"]
    assert {"artifact", "artifact_url"} <= set(output_schema["required"])
    assert output_schema["properties"]["usage"]["properties"]["llm_calls"]["maximum"] == 4
    assert manifest["input_adapters"] == ["whatsapp_zip"]
    assert manifest["artifacts"][0]["type"] == "book_pdf"
    assert "prompts/whatsapp_zip.txt" in files
    assert "modal.Volume.from_name('omo-woven-storybook-artifacts'" in files["modal_app.py"]
    assert "render_book_pdf" in files["modal_app.py"]
    assert "timeout=510" in files["modal_app.py"]


def test_unknown_adapter_and_artifact_types_emit_typed_capability_blockers() -> None:
    skill_path = ROOT / "containers" / "woven-storybook-pipeline" / "source" / "SKILL.md"
    profile_path = (
        ROOT / "packages" / "skill-to-modal" / "profiles" / "woven-storybook-pipeline.json"
    )
    skill = skill_path.read_text(encoding="utf-8")
    profile = json.loads(profile_path.read_text(encoding="utf-8"))
    profile["input_adapters"] = ["execute_chat_archive"]
    files = compiler.build_files(skill, profile)
    capabilities = json.loads(files["capability-manifest.json"])
    manifest = json.loads(files["manifest.json"])
    pricing = json.loads(files["pricing-report.json"])
    assert capabilities["decision"] == "blocked"
    assert capabilities["approved"] == []
    assert capabilities["blockers"][0]["code"] == "CAPABILITY_UNAVAILABLE"
    assert capabilities["blockers"][0]["missing_capability"] == "input.adapt:execute_chat_archive"
    assert manifest["readiness"]["can_submit"] is False
    assert manifest["pricing"]["chargeable"] is False
    assert pricing["chargeable"] is False

    profile = json.loads(profile_path.read_text(encoding="utf-8"))
    profile["artifact"]["type"] = "html_dump"
    files = compiler.build_files(skill, profile)
    capabilities = json.loads(files["capability-manifest.json"])
    blocker = capabilities["blockers"][0]
    assert blocker["code"] == "CAPABILITY_UNAVAILABLE"
    assert blocker["missing_capability"] == "artifact.render:html_dump"
    assert blocker["contract_pointer"] == "/artifact"
    assert json.loads(files["manifest.json"])["readiness"]["can_submit"] is False


def test_generic_contract_resolves_minimal_capabilities_and_chart_trigger() -> None:
    profile_path = (
        ROOT / "packages" / "skill-to-modal" / "profiles" / "woven-storybook-pipeline.json"
    )
    profile = json.loads(profile_path.read_text(encoding="utf-8"))
    profile["name"] = "synthetic-capability-contract"
    profile["slug"] = "synthetic-capability-contract"
    skill = """---
name: synthetic-capability-contract
description: A deliberately unrelated contract fixture.
---

## Workflow

1. **Transform:** Run the reviewed typed contract.
"""
    files = compiler.build_files(skill, profile)
    capabilities = json.loads(files["capability-manifest.json"])

    assert capabilities["schema_version"] == "cognition.capabilities/v2"
    assert capabilities["decision"] == "approved"
    assert [item["name"] for item in capabilities["selected"]] == [
        "book_pdf_renderer",
        "whatsapp_zip_adapter",
    ]
    assert capabilities["approved"] == [
        "book_pdf_renderer@1.0.0",
        "whatsapp_zip_adapter@1.0.0",
    ]
    assert {item["name"] for item in capabilities["needs"]} == {
        "artifact.render:book_pdf",
        "input.adapt:whatsapp_export_zip",
    }
    assert {item["name"] for item in capabilities["generated"]["dependencies"]} == {
        "artifact_store",
        "private_input_artifact_reader",
    }
    assert "render_book_pdf" in files["modal_app.py"]
    assert "prompts/whatsapp_zip.txt" in files

    chart_resolution = compiler.resolve_capabilities(
        {
            "artifacts": [
                {"kind": "metrics_viz", "content_media_type": "image/png"}
            ],
            "capabilities": [],
            "execution_kind": "single_llm",
            "output_schema": {"properties": {"chart": {"type": "object"}}},
            "readiness": {"blockers": [], "can_submit": True},
            "steps": [{"operation": "visualization.render.chart"}],
        },
        "c" * 64,
    )
    assert [item["name"] for item in chart_resolution["selected"]] == ["chart_generation"]
    assert chart_resolution["approved"] == ["chart_generation@1.0.0"]
    assert chart_resolution["generated"]["tool_bindings"] == [
        "tools.render.charts.render_chart_png"
    ]


def _video_contract_profile() -> dict:
    profile = json.loads(PROFILE_PATH.read_text(encoding="utf-8"))
    profile["steps"].append(
        {
            "id": "normalize-video",
            "type": "native",
            "provider": "local",
            "operation": "media.video.normalize",
            "execution_mode": "long_running",
            "readiness": "ready",
        }
    )
    profile["artifacts"].append(
        {"type": "video/mp4", "required": True}
    )
    profile["outputs"] = [{"kind": "run_status"}]
    profile["runtime"] = {"ownership_scope": "per_run"}
    return profile


def test_video_contract_resolves_video_and_domain_state_and_emits_runtime_pieces() -> None:
    profile = _video_contract_profile()
    files = compiler.build_files(SKILL_PATH.read_text(encoding="utf-8"), profile)
    capabilities = json.loads(files["capability-manifest.json"])

    assert [item["name"] for item in capabilities["selected"]] == [
        "domain_state",
        "video_processing",
    ]
    assert capabilities["approved"] == [
        "domain_state@1.0.0",
        "video_processing@1.0.0",
    ]
    assert {item["name"] for item in capabilities["generated"]["dependencies"]} == {
        "artifact_store",
        "ffmpeg_runtime",
    }
    assert {
        "tools.render.video.probe",
        "tools.render.video.normalize",
        "runner.domain_state.create",
        "runner.domain_state.transition",
    } <= set(capabilities["generated"]["tool_bindings"])
    modal_app = files["modal_app.py"]
    assert "REVIEWED_MEDIA_OPERATIONS = ['media.video.normalize']" in modal_app
    assert "def probe_media(" in modal_app
    assert "def run_media_step(" in modal_app
    assert "def materialize_media_artifact(" in modal_app
    assert "class InMemoryDomainState:" in modal_app
    assert "def domain_submit_response(" in modal_app
    assert "def domain_status_response(" in modal_app
    assert "def run_long_running_job(" in modal_app
    assert ".apt_install('ffmpeg')" in modal_app
    assert "video.py" in modal_app
    compile(modal_app, "generated-video-modal-app", "exec")


def test_plain_llm_contract_resolves_neither_video_nor_domain_state() -> None:
    profile = json.loads(PROFILE_PATH.read_text(encoding="utf-8"))
    resolution = compiler.resolve_capabilities(profile, "d" * 64)

    selected = {item["name"] for item in resolution["selected"]}
    assert selected.isdisjoint({"video_processing", "domain_state"})
    assert "tools.render.video.normalize" not in resolution["generated"]["tool_bindings"]
    assert "runner.domain_state.create" not in resolution["generated"]["tool_bindings"]

    unsupported = _video_contract_profile()
    unsupported["steps"][-1]["operation"] = "media.video.generative_vfx"
    blocked = compiler.resolve_capabilities(unsupported, "e" * 64)
    blocker = next(
        item for item in blocked["blockers"] if item["contract_pointer"].startswith("/steps/")
    )
    assert blocker["code"] == "CAPABILITY_UNAVAILABLE"
    assert blocker["missing_capability"] == "media.process:media.video.generative_vfx"


@pytest.mark.skipif(
    shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None,
    reason="FFmpeg/ffprobe are required for the generated media binding smoke",
)
def test_generated_video_binding_smoke_and_typed_domain_transitions(tmp_path: Path) -> None:
    profile = _video_contract_profile()
    files = compiler.build_files(SKILL_PATH.read_text(encoding="utf-8"), profile)
    output = tmp_path / "video-contract"
    assert compiler.write_or_check(files, output, check=False) == 0
    spec = importlib.util.spec_from_file_location(
        "generated_video_contract", output / "modal_app.py"
    )
    assert spec is not None and spec.loader is not None
    runtime = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(runtime)

    source = tmp_path / "fixture.mp4"
    subprocess.run(
        [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-nostdin",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "testsrc=duration=0.5:size=96x54:rate=12",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=440:duration=0.5:sample_rate=48000",
            "-map",
            "0:v:0",
            "-map",
            "1:a:0",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-threads",
            "1",
            "-c:a",
            "aac",
            "-shortest",
            source,
        ],
        check=True,
    )
    media_root = tmp_path / "media-artifacts"
    artifact = runtime.materialize_media_artifact(
        "run-video-smoke",
        "media.video.normalize",
        source,
        opts={"orientation": "portrait", "max_dimension": 160},
        output_root=media_root,
    )
    destination = media_root / artifact["object_key"]
    assert destination.is_file()
    assert artifact["content_type"] == "video/mp4"
    assert artifact["codecs"] == {"video": "h264", "audio": "aac"}
    assert artifact["width"] == 90
    assert artifact["height"] == 160
    assert len(artifact["sha256"]) == 64

    now = [1_000.0]
    state = runtime.InMemoryDomainState(clock=lambda: now[0])
    queued = state.create("owner-a", run_id="run-video-smoke", ttl_seconds=60)
    assert queued["status"] == "queued"
    assert runtime.domain_submit_response(queued)["result_url"] == "/v1/runs/run-video-smoke"
    processing = state.transition(
        "owner-a",
        queued["run_id"],
        expected_version=queued["version"],
        status="processing",
        phase="normalize",
        progress_pct=25,
    )
    assert processing["status"] == "processing"
    assert state.transition(
        "owner-a",
        queued["run_id"],
        expected_version=queued["version"],
        status="processing",
        phase="normalize",
        progress_pct=25,
    ) == processing
    done = state.transition(
        "owner-a",
        queued["run_id"],
        expected_version=processing["version"],
        status="done",
        phase="done",
        progress_pct=100,
        artifacts=[artifact],
    )
    assert done["status"] == "done"
    assert done["artifacts"][0]["sha256"] == artifact["sha256"]
    status_response = runtime.domain_status_response(
        "owner-a", queued["run_id"], state_store=state
    )
    assert status_response["status"] == "done"
    assert "owner_id" not in status_response
    with pytest.raises(runtime.DomainStateError, match="STATE_TRANSITION_INVALID"):
        state.transition(
            "owner-a",
            queued["run_id"],
            expected_version=done["version"],
            status="processing",
            phase="backward",
            progress_pct=100,
        )
    with pytest.raises(runtime.DomainStateError, match="STATE_NOT_FOUND"):
        state.read_owned("owner-b", queued["run_id"])
    now[0] += 61
    with pytest.raises(runtime.DomainStateError, match="STATE_EXPIRED"):
        state.read_owned("owner-a", queued["run_id"])
    assert state.expire("owner-a", queued["run_id"])["status"] == "done"


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

    denied_value = {
        "words": [
            item("thee", "th"),
            item("these", "th"),
            item("three", "th"),
            item("teeth", "ee"),
            item("tree", "ee"),
            item("beetle", "ee"),
            item("sheep", "ee"),
            item("thrush", "th"),
        ],
        "coverage": ["th", "ee"],
        "warnings": [],
    }
    denied_payload = {
        "phonemes": ["th", "ee"],
        "topic": "animals and nature",
        "difficulty_level": "beginner",
        "dialect": "en-AU",
        "word_count": 6,
    }
    filtered, denied_diff = runtime._candidate(json.dumps(denied_value), denied_payload)
    assert denied_diff == ""
    assert filtered is not None
    assert [entry["word"] for entry in filtered["words"]] == [
        "three",
        "teeth",
        "tree",
        "beetle",
        "sheep",
        "thrush",
    ]

    underflow_value = {**denied_value, "words": denied_value["words"][:-1]}
    _underflow, underflow_diff = runtime._candidate(
        json.dumps(underflow_value), denied_payload
    )
    assert "semantic_word_count(expected=6,actual=5)" in underflow_diff
    assert "thee" not in underflow_diff
    assert "these" not in underflow_diff

    decodable, _profile = _generated_runtime_for(
        tmp_path, "decodable-sentence-creator"
    )
    decodable_payload = {
        "phonics_patterns": ["long_a", "ai_vowel_team"],
        "num_sentences": 1,
        "sentence_length": "medium",
        "include_sight_words": True,
        "dialect": "en-GB",
    }
    decodable_value = {
        "sentences": [
            {
                "text": "She waits for the train at the station.",
                "target_words": ["waits", "train", "station"],
                "sight_or_irregular_words": ["she", "for", "the", "at"],
            }
        ],
        "coverage": ["long_a", "ai_vowel_team"],
        "warnings": [],
    }
    filtered_targets, target_diff = decodable._candidate(
        json.dumps(decodable_value), decodable_payload
    )
    assert target_diff == ""
    assert filtered_targets is not None
    assert filtered_targets["sentences"][0]["target_words"] == ["waits", "train"]
    assert filtered_targets["coverage"] == ["long_a", "ai_vowel_team"]

    all_invalid = json.loads(json.dumps(decodable_value))
    all_invalid["sentences"][0]["target_words"] = ["station"]
    _empty_targets, empty_target_diff = decodable._candidate(
        json.dumps(all_invalid), decodable_payload
    )
    assert "semantic_target_containment" in empty_target_diff
    assert "station" not in empty_target_diff

    syllable, _profile = _generated_runtime_for(
        tmp_path, "syllable-splitter-and-counter"
    )
    dots_payload = {
        "words": ["family", "chocolate", "camera"],
        "dialect": "en-GB",
        "notation": "dots",
    }
    dots_value = {
        "items": [
            {"word": "family", "syllabified": "fam-i-ly", "syllable_count": 3, "ambiguity_note": ""},
            {"word": "chocolate", "syllabified": "choc-o-late", "syllable_count": 3, "ambiguity_note": ""},
            {"word": "camera", "syllabified": "cam-er-a", "syllable_count": 3, "ambiguity_note": ""},
        ],
        "warnings": [],
    }
    normalized_dots, dots_diff = syllable._candidate(json.dumps(dots_value), dots_payload)
    assert dots_diff == ""
    assert normalized_dots is not None
    assert [item["syllabified"] for item in normalized_dots["items"]] == [
        "fam.i.ly",
        "choc.o.late",
        "cam.er.a",
    ]

    ipa_payload = {
        "words": ["fire", "poem", "comfortable"],
        "dialect": "en-AU",
        "notation": "hyphen",
    }
    ipa_value = {
        "items": [
            {"word": "fire", "syllabified": "fai·ə", "syllable_count": 2, "ambiguity_note": ""},
            {"word": "poem", "syllabified": "pəʊ·əm", "syllable_count": 2, "ambiguity_note": ""},
            {"word": "comfortable", "syllabified": "ˈkʌmf·tə·bəl", "syllable_count": 3, "ambiguity_note": ""},
        ],
        "warnings": [],
    }
    preserved_ipa, ipa_diff = syllable._candidate(json.dumps(ipa_value), ipa_payload)
    assert preserved_ipa is not None
    assert preserved_ipa["items"][0]["syllabified"] == "fai·ə"
    assert "semantic_spelling_preservation" in ipa_diff

    swapped = json.loads(json.dumps(dots_value))
    swapped["items"][0], swapped["items"][1] = swapped["items"][1], swapped["items"][0]
    _swapped, swapped_diff = syllable._candidate(json.dumps(swapped), dots_payload)
    assert "semantic_word_order" in swapped_diff


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
