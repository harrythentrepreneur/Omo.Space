"""Unit tests for deterministic, data-only SKILL.md compilation."""

from __future__ import annotations

import asyncio
import hashlib
import importlib.util
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator


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
SEMANTIC_REPLAY_PATH = (
    ROOT
    / "packages"
    / "skill-to-modal"
    / "tests"
    / "fixtures"
    / "semantic-adapter-real-runs.json"
)
SEMANTIC_INPUTS_PATH = SEMANTIC_REPLAY_PATH.with_name("semantic-adapter-inputs.json")
HARDENING_FIXTURE_PATH = SEMANTIC_REPLAY_PATH.with_name(
    "hardening-final-rerun.json"
)
PINNED_MEDIA_RUNTIME_VERSION = compiler.PLATFORM_CAPABILITY_DEPENDENCIES["ffmpeg_runtime"]["version"]


def _has_pinned_media_runtime() -> bool:
    """Run the real media smoke only against the reviewed binary release."""

    for executable in ("ffmpeg", "ffprobe"):
        if shutil.which(executable) is None:
            return False
        try:
            result = subprocess.run(
                [executable, "-version"],
                check=True,
                capture_output=True,
                text=True,
                shell=False,
                timeout=20,
            )
        except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
            return False
        first_line = result.stdout.splitlines()[0] if result.stdout else ""
        matched = re.match(rf"^{re.escape(executable)} version ([^ ]+)", first_line)
        if not matched or matched.group(1) != PINNED_MEDIA_RUNTIME_VERSION:
            return False
    return True


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


def test_generated_runtime_imports_from_flat_modal_root() -> None:
    profile = json.loads(PROFILE_PATH.read_text(encoding="utf-8"))
    source = compiler.modal_app_template(profile)
    namespace = {"__file__": "/root/modal_app.py", "__name__": "flat_modal_runtime"}
    exec(compile(source, "/root/modal_app.py", "exec"), namespace)
    assert namespace["LOCAL_ROOT"] == Path("/root")
    assert namespace["RENDER_ROOT"] == Path("/root/tools/render")
    assert namespace["RESEARCH_ROOT"] == Path("/root/tools/research")


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


def test_missing_profile_readiness_fails_with_typed_contract_error() -> None:
    skill = SKILL_PATH.read_text(encoding="utf-8")
    profile = json.loads(PROFILE_PATH.read_text(encoding="utf-8"))
    profile.pop("readiness")

    with pytest.raises(ValueError, match="profile readiness must contain typed can_submit and blockers"):
        compiler.build_files(skill, profile)

    profile["readiness"] = {"can_submit": False, "blockers": [{}]}
    with pytest.raises(ValueError, match="profile readiness must contain typed can_submit and blockers"):
        compiler.build_files(skill, profile)

    profile["readiness"] = {"can_submit": False, "blockers": [{"code": 7, "detail": "blocked"}]}
    with pytest.raises(ValueError, match="profile readiness must contain typed can_submit and blockers"):
        compiler.build_files(skill, profile)


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
    assert [item["name"] for item in chart_resolution["selected"]] == [
        "chart_generation",
        "tabular.statistics",
    ]
    assert chart_resolution["approved"] == [
        "chart_generation@1.0.0",
        "tabular.statistics@1.0.0",
    ]
    assert set(chart_resolution["generated"]["tool_bindings"]) == {
        "tools.render.charts.render_chart_png",
        "tools.render.tabular.analyze_csv",
        "tools.render.tabular.parse_csv",
        "tools.render.tabular.statistics",
    }


def test_resolver_selects_public_search_fetch_from_operations_and_legacy_adapter() -> None:
    resolution = compiler.resolve_capabilities(
        {
            "artifacts": [],
            "capabilities": [],
            "execution_kind": "single_llm",
            "input_adapters": ["browser_research"],
            "outputs": [],
            "readiness": {"blockers": [], "can_submit": True},
            "steps": [
                {"operation": "research.collect.public_search"},
                {"operation": "research.collect.web_fetch", "source_class": "primary_source"},
            ],
        },
        "f" * 64,
    )

    assert [item["name"] for item in resolution["selected"]] == [
        "research.collect:public_search_fetch"
    ]
    assert resolution["approved"] == ["research.collect:public_search_fetch@1.0.0"]
    assert resolution["blockers"] == []
    assert {item["name"] for item in resolution["needs"]} == {
        "input.adapt:browser_research",
        "research.collect:public_search_fetch",
    }
    assert resolution["generated"]["tool_bindings"] == [
        "tools.research.public_fetch.fetch_public_url",
        "tools.research.public_fetch.search_snippets",
    ]


def test_resolver_selects_tabular_statistics_from_steps_adapter_and_artifacts() -> None:
    resolution = compiler.resolve_capabilities(
        {
            "artifacts": [],
            "capabilities": [],
            "execution_kind": "single_llm",
            "input_adapters": ["tabular_dataset"],
            "outputs": [{"kind": "tabular_analysis"}],
            "readiness": {"blockers": [], "can_submit": True},
            "steps": [
                {"operation": "tabular.parse"},
                {"operation": "statistics.compute"},
            ],
        },
        "a" * 64,
    )

    assert [item["name"] for item in resolution["selected"]] == [
        "tabular.statistics"
    ]
    assert resolution["approved"] == ["tabular.statistics@1.0.0"]
    assert resolution["blockers"] == []
    assert {item["name"] for item in resolution["needs"]} == {
        "input.adapt:tabular_dataset",
        "tabular.statistics",
    }
    assert resolution["generated"]["tool_bindings"] == [
        "tools.render.tabular.analyze_csv",
        "tools.render.tabular.parse_csv",
        "tools.render.tabular.statistics",
    ]

    metrics_resolution = compiler.resolve_capabilities(
        {
            "artifacts": [
                {"kind": "metrics_viz", "content_media_type": "image/png"}
            ],
            "capabilities": [],
            "execution_kind": "single_llm",
            "outputs": [],
            "readiness": {"blockers": [], "can_submit": True},
            "steps": [],
        },
        "b" * 64,
    )
    assert {item["name"] for item in metrics_resolution["selected"]} == {
        "chart_generation",
        "tabular.statistics",
    }

    analysis_artifact_resolution = compiler.resolve_capabilities(
        {
            "artifacts": [{"kind": "tabular_analysis"}],
            "capabilities": [],
            "execution_kind": "single_llm",
            "outputs": [],
            "readiness": {"blockers": [], "can_submit": True},
            "steps": [],
        },
        "e" * 64,
    )
    assert [item["name"] for item in analysis_artifact_resolution["selected"]] == [
        "tabular.statistics"
    ]
    assert analysis_artifact_resolution["decision"] == "approved"
    assert analysis_artifact_resolution["blockers"] == []


def _hardening_tabular_profile() -> dict:
    profile = json.loads(PROFILE_PATH.read_text(encoding="utf-8"))
    profile["name"] = "hardening-tabular-analysis"
    profile["slug"] = "hardening-tabular-analysis"
    profile["input_adapters"] = ["tabular_dataset"]
    profile["steps"] = [
        {"operation": "tabular.parse"},
        {"operation": "statistics.compute"},
        {"operation": "visualization.render.chart"},
    ]
    profile["outputs"] = [
        {
            "content_media_type": "application/json",
            "name": "analysis",
            "semantic_type": "statistical_analysis",
        },
        {
            "artifact_type": "chart",
            "content_media_type": "image/png",
            "kind": "chart",
            "name": "chart",
        },
    ]
    profile["artifacts"] = []
    profile["artifact"] = {
        "content_media_type": "image/png",
        "filename": "analysis-chart.png",
        "kind": "chart",
        "signed_url_ttl_seconds": 3600,
        "signing_key_env": "LLM_API_KEY",
        "source_field": "chart_spec",
        "type": "chart_png",
        "volume_name": "omo-hardening-tabular-artifacts",
    }
    profile["output_schema"] = {
        "additionalProperties": False,
        "properties": {
            "summary": {"type": "string"},
            "findings": {"items": {"type": "string"}, "type": "array"},
            "chart_spec": {"type": "object"},
        },
        "required": ["summary", "findings", "chart_spec"],
        "type": "object",
    }
    return profile


def test_resolver_selects_tabular_analysis_orchestrator_for_combined_contract() -> None:
    resolution = compiler.resolve_capabilities(_hardening_tabular_profile(), "9" * 64)

    assert [item["name"] for item in resolution["selected"]] == [
        "chart_generation",
        "tabular.statistics",
        "tabular_analysis_orchestrator",
    ]
    assert resolution["decision"] == "approved"
    assert resolution["blockers"] == []
    assert "tabular.analysis.orchestrate" in {
        item["name"] for item in resolution["needs"]
    }
    assert {
        "tools.render.tabular.parse_csv",
        "tools.render.tabular.statistics",
        "tools.render.charts.render_chart_png",
    } <= set(resolution["generated"]["tool_bindings"])


def test_final_rerun_data_fixtures_run_full_grounded_pipeline_and_render_png(
    tmp_path: Path,
) -> None:
    fixture = json.loads(HARDENING_FIXTURE_PATH.read_text(encoding="utf-8"))
    source = compiler.modal_app_template(_hardening_tabular_profile())
    runtime_path = tmp_path / "generated_tabular_orchestrator.py"
    runtime_path.write_text(source, encoding="utf-8")
    spec = importlib.util.spec_from_file_location(
        "generated_tabular_orchestrator", runtime_path
    )
    assert spec is not None and spec.loader is not None
    runtime = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(runtime)

    for case in fixture["data_analysis"]:
        payload = case["input"]
        assert compiler.sha256_text(
            json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        ) == case["input_sha256"]
        writer_calls = []

        def fixture_writer(grounded_payload: dict, *, _case=case) -> dict:
            writer_calls.append(grounded_payload)
            assert set(grounded_payload) == {
                "questions",
                "hypotheses",
                "column_semantics",
                "filters",
                "units",
                "computed_stats",
            }
            assert "dataset" not in grounded_payload
            assert "rows" not in grounded_payload["computed_stats"]
            return json.loads(json.dumps(_case["findings_writer_output"]))

        result = runtime.run_tabular_analysis_orchestrator(
            payload,
            findings_writer=fixture_writer,
            output_root=tmp_path / case["id"],
        )
        assert set(result) == {
            "summary", "findings", "chart_spec", "artifact_path", "stats"
        }
        assert len(writer_calls) == 1
        artifact_path = Path(result["artifact_path"])
        assert artifact_path.is_file()
        assert artifact_path.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
        from PIL import Image

        with Image.open(artifact_path) as rendered:
            rendered.verify()
        grouped = result["stats"]["grouped_sums"][0]
        if case["id"] == "reviewed-happy-path":
            assert {item["key"]: item["sum"] for item in grouped["groups"]} == {
                "North": 260,
                "South": 90,
            }
            assert result["chart_spec"]["kind"] == "bar"
        else:
            assert result["chart_spec"]["kind"] == "line"

    bad_payload = fixture["data_analysis"][0]["input"]
    with pytest.raises(ValueError, match="TABULAR_FINDINGS_UNGROUNDED_NUMBER"):
        runtime.run_tabular_analysis_orchestrator(
            bad_payload,
            findings_writer=lambda _stats: {
                "summary": "The result is 777.",
                "findings": ["No computed statistic supports 777."],
            },
            output_root=tmp_path / "ungrounded",
        )

    too_many_rows = json.loads(json.dumps(bad_payload))
    too_many_rows["dataset"] = "group,value\n" + "\n".join(
        f"g{index % 2},{index}" for index in range(5001)
    )
    writer_called = []
    with pytest.raises(ValueError, match="TABULAR_TOO_MANY_ROWS"):
        runtime.run_tabular_analysis_orchestrator(
            too_many_rows,
            findings_writer=lambda _stats: writer_called.append(True),
            output_root=tmp_path / "too-many-rows",
        )
    assert writer_called == []


def _domain_analysis_profile(domain: str, summary_field: str, findings_field: str) -> dict:
    profile = _hardening_tabular_profile()
    profile["name"] = domain.lower().replace(" ", "-")
    profile["slug"] = profile["name"]
    profile["DOMAIN"] = domain
    profile["steps"] = [
        {"id": "parse", "operation": "tabular.parse", "type": "tool"},
        {"id": "statistics", "operation": "statistics.compute", "type": "tool"},
        {
            "id": "findings",
            "operation": "chat.completions.strict_json",
            "type": "llm",
        },
        {
            "id": "chart",
            "operation": "visualization.render.chart",
            "type": "tool",
        },
    ]
    findings_schema = {
        "additionalProperties": False,
        "properties": {
            summary_field: {"minLength": 3, "type": "string"},
            findings_field: {
                "items": {"minLength": 3, "type": "string"},
                "minItems": 1,
                "type": "array",
            },
        },
        "required": [summary_field, findings_field],
        "type": "object",
    }
    profile["live"]["model_output_schema"] = findings_schema
    profile["output_schema"] = {
        "additionalProperties": False,
        "properties": {
            **findings_schema["properties"],
            "chart_spec": {"type": "object"},
        },
        "required": [summary_field, findings_field, "chart_spec"],
        "type": "object",
    }
    return profile


@pytest.mark.parametrize(
    ("domain", "summary_field", "findings_field"),
    [
        ("Marketing Analytics", "marketing_summary", "marketing_findings"),
        ("Churn Analysis", "risk_summary", "risk_findings"),
        ("Expense Categorization", "spend_summary", "category_findings"),
    ],
)
def test_generic_domain_orchestrator_resolves_and_runs_stats_only_contracts(
    tmp_path: Path,
    domain: str,
    summary_field: str,
    findings_field: str,
) -> None:
    profile = _domain_analysis_profile(domain, summary_field, findings_field)
    resolution = compiler.resolve_capabilities(profile, "d" * 64)
    selected = [item["name"] for item in resolution["selected"]]

    assert selected == [
        "chart_generation",
        "domain_analysis_orchestrator",
        "tabular.statistics",
    ]
    assert "tabular_analysis_orchestrator" not in selected
    assert resolution["decision"] == "approved"
    prompt = compiler.domain_analysis_prompt(profile)
    assert prompt.startswith(f"DOMAIN: {domain}\n")
    assert summary_field in prompt and findings_field in prompt

    runtime_path = tmp_path / f"{profile['slug']}.py"
    runtime_path.write_text(compiler.modal_app_template(profile), encoding="utf-8")
    spec = importlib.util.spec_from_file_location(profile["slug"].replace("-", "_"), runtime_path)
    assert spec is not None and spec.loader is not None
    runtime = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(runtime)
    observed = []

    def fixture_writer(grounded: dict) -> dict:
        observed.append(grounded)
        assert grounded["DOMAIN"] == domain
        assert set(grounded) == {
            "DOMAIN",
            "expected_output_fields",
            "questions",
            "hypotheses",
            "column_semantics",
            "filters",
            "units",
            "computed_stats",
        }
        assert "dataset" not in grounded
        assert "rows" not in grounded["computed_stats"]
        return {
            summary_field: "The computed row count is 2.",
            findings_field: ["The computed value total is 30."],
        }

    result = runtime.run_domain_analysis_orchestrator(
        {
            "dataset": "segment,value\nA,10\nB,20\n",
            "dataset_format": "csv",
            "questions": ["Summarize the supplied values."],
            "hypotheses": [],
            "column_semantics": "segment is categorical and value is numeric",
            "filters": "None",
            "units": "count",
        },
        findings_writer=fixture_writer,
    )
    Draft202012Validator(profile["output_schema"]).validate(result)
    assert len(observed) == 1
    assert runtime.run_domain_analysis_orchestrator.__name__ == "run_domain_analysis_orchestrator"


def test_domain_orchestrator_code_path_is_identical_and_rejects_ungrounded_numbers(
    tmp_path: Path,
) -> None:
    bytecodes = []
    runtimes = []
    for index, args in enumerate(
        [
            ("Marketing Analytics", "marketing_summary", "marketing_findings"),
            ("Churn Analysis", "risk_summary", "risk_findings"),
            ("Expense Categorization", "spend_summary", "category_findings"),
        ]
    ):
        profile = _domain_analysis_profile(*args)
        runtime_path = tmp_path / f"domain_runtime_{index}.py"
        runtime_path.write_text(compiler.modal_app_template(profile), encoding="utf-8")
        spec = importlib.util.spec_from_file_location(f"domain_runtime_{index}", runtime_path)
        assert spec is not None and spec.loader is not None
        runtime = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(runtime)
        runtimes.append((runtime, args))
        bytecodes.append(runtime.run_domain_analysis_orchestrator.__code__.co_code)
    assert bytecodes[0] == bytecodes[1] == bytecodes[2]

    runtime, (_, summary_field, findings_field) = runtimes[0]
    with pytest.raises(ValueError, match="DOMAIN_FINDINGS_UNGROUNDED_NUMBER"):
        runtime.run_domain_analysis_orchestrator(
            {
                "dataset": "segment,value\nA,10\nB,20\n",
                "dataset_format": "csv",
                "questions": ["Summarize the supplied values."],
                "hypotheses": [],
                "column_semantics": "segment and value",
                "filters": "None",
                "units": "count",
            },
            findings_writer=lambda _grounded: {
                summary_field: "The unsupported result is 777.",
                findings_field: ["No computed statistic supports that claim."],
            },
        )


def test_tabular_hosted_submit_run_result_executes_bounded_program_and_returns_artifact(
    tmp_path: Path,
) -> None:
    profile = _hardening_tabular_profile()
    profile["input_schema"] = {
        "additionalProperties": False,
        "properties": {
            "dataset": {"minLength": 10, "type": "string"},
            "dataset_format": {"const": "csv"},
            "questions": {"items": {"type": "string"}, "minItems": 1, "type": "array"},
            "hypotheses": {"items": {"type": "string"}, "type": "array"},
            "column_semantics": {"type": "string"},
            "filters": {"type": "string"},
            "units": {"type": "string"},
        },
        "required": [
            "dataset",
            "dataset_format",
            "questions",
            "hypotheses",
            "column_semantics",
            "filters",
            "units",
        ],
        "type": "object",
    }
    bundle = tmp_path / "hosted-data-analysis"
    (bundle / "schemas").mkdir(parents=True)
    (bundle / "prompts").mkdir()
    (bundle / "modal_app.py").write_text(
        compiler.modal_app_template(profile), encoding="utf-8"
    )
    (bundle / "schemas" / "input.json").write_text(
        compiler.canonical_json(compiler.runtime_input_schema(profile)), encoding="utf-8"
    )
    (bundle / "schemas" / "output.json").write_text(
        compiler.canonical_json(compiler.runtime_output_schema(profile)), encoding="utf-8"
    )
    (bundle / "manifest.json").write_text(
        compiler.canonical_json(
            {
                "readiness": {
                    "can_submit": True,
                    "blockers": [],
                    "required_env_names": profile["required_env_names"],
                }
            }
        ),
        encoding="utf-8",
    )
    (bundle / "prompts" / "tabular_analysis.txt").write_text(
        compiler.TABULAR_ANALYSIS_PROMPT, encoding="utf-8"
    )
    spec = importlib.util.spec_from_file_location("hosted_data_analysis", bundle / "modal_app.py")
    assert spec is not None and spec.loader is not None
    runtime = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(runtime)
    payload = {
        "dataset": "region,revenue\nNorth,120\nSouth,80\nNorth,100\n",
        "dataset_format": "csv",
        "questions": ["Compare region totals."],
        "hypotheses": [],
        "column_semantics": "region is categorical and revenue is numeric",
        "filters": "None",
        "units": "USD",
    }
    stored = {}
    writer_inputs = []

    def findings_writer(grounded: dict) -> dict:
        writer_inputs.append(grounded)
        assert "dataset" not in grounded
        assert "rows" not in grounded["computed_stats"]
        return {
            "summary": "North totals 220 and South totals 80.",
            "findings": ["The computed revenue sum is 300."],
        }

    def spawn_runner(submitted: dict) -> str:
        stored["fc-hosted"] = runtime.execute_workflow(
            submitted,
            findings_writer=findings_writer,
            artifact_root=tmp_path / "artifacts",
            artifact_signing_key="offline-fixture-signing-key",
            clock=lambda: 1_700_000_000,
        )
        return "fc-hosted"

    web = runtime.create_fastapi_app(
        spawn_runner=spawn_runner,
        lookup_result=lambda call_id: stored[call_id],
    )
    submit_route = next(route for route in web.routes if route.path == "/v1/runs")
    result_route = next(route for route in web.routes if route.path == "/v1/runs/{call_id}")
    accepted = asyncio.run(submit_route.endpoint(payload))
    assert accepted["status"] == "accepted"
    assert accepted["call_id"] == "fc-hosted"
    completed = asyncio.run(result_route.endpoint("fc-hosted"))

    Draft202012Validator(compiler.runtime_output_schema(profile)).validate(completed)
    artifact = completed["artifact"]
    artifact_path = tmp_path / "artifacts" / artifact["object_key"]
    assert artifact_path.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
    assert artifact["sha256"] == compiler.hashlib.sha256(artifact_path.read_bytes()).hexdigest()
    assert "expires=1700003600" in completed["artifact_url"]
    assert len(writer_inputs) == 1


def test_generated_bundle_imports_public_fetch_and_tabular_modules_and_runs_offline(
    tmp_path: Path,
) -> None:
    profile = json.loads(PROFILE_PATH.read_text(encoding="utf-8"))
    profile["input_adapters"] = ["browser_research", "tabular_dataset"]
    profile["steps"].extend(
        [
            {
                "id": "collect-primary-sources",
                "type": "native",
                "provider": "local",
                "operation": "research.collect.public_search",
                "readiness": "ready",
            },
            {
                "id": "parse-table",
                "type": "native",
                "provider": "local",
                "operation": "tabular.parse",
                "readiness": "ready",
            },
            {
                "id": "compute-statistics",
                "type": "native",
                "provider": "local",
                "operation": "statistics.compute",
                "readiness": "ready",
            },
        ]
    )
    files = compiler.build_files(SKILL_PATH.read_text(encoding="utf-8"), profile)
    modal_app = files["modal_app.py"]

    assert "from tools.research.public_fetch import (" in modal_app
    assert "from tools.render.tabular import TabularError, parse_csv, statistics" in modal_app
    assert 'RESEARCH_ROOT / "public_fetch.py"' in modal_app
    assert 'RENDER_ROOT / "tabular.py"' in modal_app
    compile(modal_app, "generated-public-tabular-modal-app", "exec")

    output = tmp_path / "public-tabular"
    assert compiler.write_or_check(files, output, check=False) == 0
    spec = importlib.util.spec_from_file_location(
        "generated_public_tabular_contract", output / "modal_app.py"
    )
    assert spec is not None and spec.loader is not None
    runtime = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(runtime)

    with pytest.raises(Exception) as exc_info:
        runtime.run_public_search("bounded primary-source query")
    assert getattr(exc_info.value, "code", None) == "SEARCH_UNAVAILABLE"
    with pytest.raises(ValueError, match="at most 500"):
        runtime.run_public_search("x" * 501)

    result = runtime.run_tabular_statistics("group,value\na,1\na,3\n")
    assert result["schema_version"] == "omo.tabular-analysis/v1"
    assert result["rows"] == [
        {"group": "a", "value": 1},
        {"group": "a", "value": 3},
    ]
    assert result["statistics"]["stats"]["value"]["mean"] == 2.0


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


def test_japanese_profile_materializes_owned_executor_and_unblocks_readiness(
    tmp_path: Path,
) -> None:
    slug = "japanese-style-story-video"
    skill_path = ROOT / "containers" / slug / "source" / "SKILL.md"
    profile_path = ROOT / "packages" / "skill-to-modal" / "profiles" / f"{slug}.json"
    profile = json.loads(profile_path.read_text(encoding="utf-8"))
    files = compiler.build_files(skill_path.read_text(encoding="utf-8"), profile)
    output = tmp_path / slug
    assert compiler.write_or_check(files, output, check=False) == 0

    manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    capabilities = json.loads(
        (output / "capability-manifest.json").read_text(encoding="utf-8")
    )
    pricing = json.loads((output / "pricing-report.json").read_text(encoding="utf-8"))
    assert manifest["readiness"]["can_submit"] is True
    assert manifest["readiness"]["blockers"] == []
    assert manifest["pricing"] == {
        "chargeable": True,
        "currency": "USD",
        "display_price_usd": 0.1,
        "label": "$0.10 per run",
        "quote_status": "measured_sample_lane",
        "report_path": "pricing-report.json",
    }
    assert capabilities["decision"] == "approved"
    assert [item["name"] for item in capabilities["selected"]] == [
        "domain_state",
        "video_processing",
    ]
    assert capabilities["blockers"] == []
    assert capabilities["workflow_blockers"] == []
    assert [item["id"] for item in capabilities["skill_owned_resources"]] == [
        "japanese_procedural_sumi_e_v1"
    ]
    assert pricing["display_price_usd"] == 0.1
    assert pricing["chargeable"] is True
    assert pricing["measured_evidence"][0]["provider_cost_usd"] == 0
    assert pricing["measured_evidence"][0]["compute_cost_usd"] == 0.00061482
    assert pricing["measured_evidence"][0]["canonical_price_usd"] == 0.1
    assert (output / "resources" / "demello_resource" / "image_gen.py").read_bytes() == (
        ROOT / "containers" / "demello-awake" / "image_gen.py"
    ).read_bytes()
    assert (output / "resources" / "demello_resource" / "workflow.py").is_file()
    assert (output / "resources" / "demello_resource" / "media.py").is_file()
    assert (
        output
        / "resources"
        / "demello_resource"
        / "assets"
        / "sample-demello-10s.m4a"
    ).read_bytes() == (
        ROOT / "containers" / "demello-awake" / "assets" / "sample-demello-10s.m4a"
    ).read_bytes()
    generated_runtime = (output / "modal_app.py").read_text(encoding="utf-8")
    assert "def run_sample_pipeline(" in generated_runtime
    assert "ProceduralSumiEGenerator" not in generated_runtime
    assert ".add_local_dir(LOCAL_ROOT / \"resources\"" in generated_runtime
    assert "@modal.asgi_app(requires_proxy_auth=True)" in generated_runtime
    compile(generated_runtime, "generated-japanese-modal-app", "exec")


def test_skill_owned_resource_is_slug_locked() -> None:
    profile = json.loads(PROFILE_PATH.read_text(encoding="utf-8"))
    profile["skill_owned_resource"] = "japanese_procedural_sumi_e_v1"
    with pytest.raises(ValueError, match="another slug"):
        compiler.build_files(SKILL_PATH.read_text(encoding="utf-8"), profile)


def test_label_normalizer_resource_manifest_attests_reviewed_source() -> None:
    profile = json.loads(
        (ROOT / "packages" / "skill-to-modal" / "profiles" / "label-normalizer-canary.json").read_text(
            encoding="utf-8"
        )
    )
    manifest = compiler.skill_owned_resource_manifest(profile)
    assert manifest[0]["reviewed_source_sha256"] == (
        "32a9e56a4c3ff57fce713d5341c48a5a1b54deee7cd7369a5cda7f9eb50fea0a"
    )
    assert manifest[0]["digest"].startswith("sha256:")


def test_loader_owned_resource_compiles_to_secret_free_builder_surface(tmp_path: Path) -> None:
    slug = "skill-md-to-hosted-workflow"
    skill_path = ROOT / "containers" / slug / "source" / "SKILL.md"
    profile_path = ROOT / "packages" / "skill-to-modal" / "profiles" / f"{slug}.json"
    profile = json.loads(profile_path.read_text(encoding="utf-8"))
    files = compiler.build_files(skill_path.read_text(encoding="utf-8"), profile)
    output = tmp_path / slug
    assert compiler.write_or_check(files, output, check=False) == 0

    manifest = json.loads(files["manifest.json"])
    capabilities = json.loads(files["capability-manifest.json"])
    pricing = json.loads(files["pricing-report.json"])
    runtime = files["modal_app.py"]
    assert manifest["readiness"]["can_submit"] is True
    assert manifest["pricing"]["display_price_usd"] == 5.0
    assert manifest["pricing"]["chargeable"] is True
    assert pricing["markup"] == 5.0
    assert pricing["floor_usd"] == 0.1
    assert capabilities["approved"] == []
    assert [item["id"] for item in capabilities["skill_owned_resources"]] == [
        "deterministic_skill_loader_v1"
    ]
    assert "@modal.asgi_app(requires_proxy_auth=True)" in runtime
    assert "modal.Secret" not in runtime
    assert "COMPILER.build_files" in runtime
    assert "provider_calls\": 0" in runtime
    assert "LOCAL_ROOT.parents[1]" not in runtime
    assert "_runtime_repository_root" in runtime
    compile(runtime, "generated-loader-modal-app", "exec")


PURE_DATA_PROFILE_PATH = (
    ROOT / "packages" / "skill-to-modal" / "profiles" / "dummy-word-list-organizer.json"
)
PURE_DATA_SKILL_PATH = (
    ROOT / "packages" / "skill-to-modal" / "tests" / "fixtures" / "pure-data" / "dummy-word-list-organizer" / "SKILL.md"
)


def _pure_data_fixture() -> tuple[str, dict]:
    skill = PURE_DATA_SKILL_PATH.read_text(encoding="utf-8")
    profile = json.loads(PURE_DATA_PROFILE_PATH.read_text(encoding="utf-8"))
    return skill, profile


def test_pure_data_compiles_canonical_program_with_exact_provenance_and_executes_fixture(
    tmp_path: Path,
) -> None:
    skill, profile = _pure_data_fixture()
    source_sha256 = hashlib.sha256(skill.encode("utf-8")).hexdigest()
    assert profile["reviewed_source_sha256"] == source_sha256

    files = compiler.build_files(skill, profile)
    manifest = json.loads(files["manifest.json"])
    program = profile["pure_data_program"]
    assert files["runtime/pure-data-program.json"] == compiler.PURE_DATA_RUNTIME.canonical_pure_data_program(program) + "\n"
    assert files["runtime/pure_data_runtime.py"] == compiler.PURE_DATA_RUNTIME_PATH.read_text(encoding="utf-8")
    assert manifest["pure_data"] == {
        "program_digest": "sha256:40103f810402ebed176e4bb38e9d1c30bbe7bd4c27f515422f7007a35797d3fd",
        "program_path": "runtime/pure-data-program.json",
        "provenance": {
            "compiler_version": compiler.COMPILER_VERSION,
            "profile_version": "1.0.0",
            "reviewed_source_sha256": source_sha256,
        },
    }
    assert manifest["providers"] == []
    assert manifest["required_env_names"] == []
    assert manifest["artifacts"] == []

    output = tmp_path / "pure-data-word-list"
    assert compiler.write_or_check(files, output, check=False) == 0
    spec = importlib.util.spec_from_file_location("generated_pure_data", output / "modal_app.py")
    assert spec is not None and spec.loader is not None
    runtime = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(runtime)
    assert runtime.execute_workflow(profile["happy_path"]["input"]) == profile["happy_path"]["output"]
    source = files["modal_app.py"]
    assert all(token not in source for token in ("eval(", "exec(", "subprocess", "modal.Secret", "urllib", "requests"))


def test_pure_data_poll_binds_modal_call_to_owner_scoped_run(tmp_path: Path) -> None:
    skill, profile = _pure_data_fixture()
    files = compiler.build_files(skill, profile)
    output = tmp_path / "pure-data-owner-scope"
    assert compiler.write_or_check(files, output, check=False) == 0
    spec = importlib.util.spec_from_file_location(
        "generated_pure_data_owner_scope", output / "modal_app.py"
    )
    assert spec is not None and spec.loader is not None
    runtime = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(runtime)

    looked_up: list[str] = []

    def lookup(call_id: str) -> dict:
        looked_up.append(call_id)
        return profile["happy_path"]["output"]

    web = runtime.create_fastapi_app(
        spawn_runner=lambda _envelope: "fc-owned",
        lookup_result=lookup,
    )
    submit = next(route for route in web.routes if route.path == "/v1/runs")
    poll = next(route for route in web.routes if route.path == "/v1/runs/{run_id}")
    accepted = asyncio.run(
        submit.endpoint(profile["happy_path"]["input"], x_omo_owner_id="owner-1")
    )
    access_token = accepted["result_url"].split("access_token=", 1)[1]

    with pytest.raises(Exception) as error:
        asyncio.run(
            poll.endpoint(
                accepted["run_id"],
                call_id="fc-other",
                access_token=access_token,
                x_omo_owner_id="owner-1",
            )
        )
    assert getattr(error.value, "status_code", None) == 404
    assert looked_up == []

    assert asyncio.run(
        poll.endpoint(
            accepted["run_id"],
            call_id="fc-owned",
            access_token=access_token,
            x_omo_owner_id="owner-1",
        )
    ) == profile["happy_path"]["output"]
    assert looked_up == ["fc-owned"]


def test_pure_data_generated_contract_documents_owner_scoped_polling() -> None:
    skill, profile = _pure_data_fixture()
    files = compiler.build_files(skill, profile)
    manifest = json.loads(files["manifest.json"])
    readme = files["README.md"]
    container = files["container.yaml"]

    assert manifest["endpoint"]["poll_path_template"] == "/v1/runs/{run_id}"
    assert "  result_path: /v1/runs/{run_id}\n" in container
    assert "  result_query: call_id,access_token\n" in container
    assert "GET /v1/runs/{run_id}?call_id={call_id}&access_token={access_token}" in readme
    assert "GET /v1/runs/{call_id}" not in readme
    assert "deterministic provider-free job" in readme
    assert "provider-backed job" not in readme
    assert "named Modal secret" not in readme
    assert "Blocked release: `503`" not in readme
    assert "  not_ready_status: 503\n" not in container


def test_pure_data_requires_exact_reviewed_source_hash() -> None:
    skill, profile = _pure_data_fixture()
    profile["reviewed_source_sha256"] = "0" * 64
    with pytest.raises(ValueError, match="reviewed source SHA-256"):
        compiler.build_files(skill, profile)


def test_pure_data_profile_is_closed_and_effect_free() -> None:
    skill, profile = _pure_data_fixture()
    assert profile["execution_kind"] == "pure_data"
    for field in ("apt_packages", "artifacts", "capabilities", "required_env_names"):
        assert profile[field] == []
    assert profile["prompts"] == {}
    assert "live" not in profile
    assert all("provider" not in step for step in profile["steps"])

    for field, value in (
        ("capabilities", ["network"]),
        ("required_env_names", ["API_KEY"]),
        ("artifacts", [{"kind": "file"}]),
    ):
        poisoned = json.loads(json.dumps(profile))
        poisoned[field] = value
        with pytest.raises(ValueError, match="provider-free|effect-free"):
            compiler.build_files(skill, poisoned)

    open_schema = json.loads(json.dumps(profile))
    open_schema["input_schema"]["additionalProperties"] = True
    with pytest.raises(ValueError, match="reject unknown fields"):
        compiler.build_files(skill, open_schema)


def test_obsolete_deterministic_program_execution_kind_is_rejected() -> None:
    skill, profile = _pure_data_fixture()
    profile["execution_kind"] = "deterministic_program"
    profile["deterministic_program"] = profile.pop("pure_data_program")
    with pytest.raises(ValueError, match="execution kind"):
        compiler.build_files(skill, profile)


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


def test_generated_video_binding_rejects_unpinned_media_runtime(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    profile = _video_contract_profile()
    files = compiler.build_files(SKILL_PATH.read_text(encoding="utf-8"), profile)
    output = tmp_path / "video-contract-mismatch"
    assert compiler.write_or_check(files, output, check=False) == 0
    # Mirror the generated Modal image: compiler.py bundles the reviewed
    # renderer beside modal_app.py as /root/omo_video_renderer.py. The test
    # must not rely on this repository's `tools` namespace winning import
    # precedence over installed packages in the trusted builder image.
    shutil.copyfile(ROOT / "tools" / "render" / "video.py", output / "omo_video_renderer.py")
    monkeypatch.syspath_prepend(str(output))
    spec = importlib.util.spec_from_file_location(
        "generated_video_contract_mismatch", output / "modal_app.py"
    )
    assert spec is not None and spec.loader is not None
    runtime = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(runtime)
    assert runtime.FFMPEG_RUNTIME_VERSION == PINNED_MEDIA_RUNTIME_VERSION

    def fake_version(command, **_kwargs):
        executable = str(command[0])
        return subprocess.CompletedProcess(
            command, 0, stdout=f"{executable} version 8.0.1-host\n", stderr=""
        )

    monkeypatch.setattr(runtime.subprocess, "run", fake_version)
    error_type = runtime._video_tools()["error"]
    with pytest.raises(error_type) as raised:
        runtime.ffmpeg_runtime_version()
    assert raised.value.code == "FFMPEG_VERSION_MISMATCH"
    assert "8.0.1-host" in str(raised.value)


@pytest.mark.skipif(
    not _has_pinned_media_runtime(),
    reason="the exact pinned FFmpeg/ffprobe runtime is required for the real media smoke",
)
def test_generated_video_binding_real_media_smoke(tmp_path: Path) -> None:
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


def test_generated_video_binding_typed_domain_transitions(tmp_path: Path) -> None:
    profile = _video_contract_profile()
    files = compiler.build_files(SKILL_PATH.read_text(encoding="utf-8"), profile)
    output = tmp_path / "video-domain-state-contract"
    assert compiler.write_or_check(files, output, check=False) == 0
    spec = importlib.util.spec_from_file_location(
        "generated_video_domain_state_contract", output / "modal_app.py"
    )
    assert spec is not None and spec.loader is not None
    runtime = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(runtime)

    artifact = {
        "object_key": "runs/run-video-smoke/normalized.mp4",
        "content_type": "video/mp4",
        "codecs": {"video": "h264", "audio": "aac"},
        "width": 90,
        "height": 160,
        "sha256": "a" * 64,
    }
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


_WRAPPER_OUTPUT_FIELDS = {"run_id", "status", "workflow_version", "usage"}
_SEMANTIC_PROMISES = {
    "copy-editing": {
        "constraints": ["Use only supplied facts", "Return a revised draft with before/after revision evidence"],
        "source_expected_contract": {"outputs": "A revised draft and revision report."},
    },
    "internal-comms": {
        "constraints": ["Use only supplied facts"],
        "source_expected_contract": {"inputs": "Source facts", "outputs": "Key points."},
    },
    "contract-review": {
        "constraints": ["Quote only supplied language", "Always include a disclaimer"],
        "source_expected_contract": {"outputs": "Risks, obligations, and legal-review disclaimer."},
    },
    "note-taking": {
        "constraints": ["Action source quotes must be exact"],
        "source_expected_contract": {"outputs": "Structured Markdown note with summary and action items."},
    },
    "invoice-processing": {
        "constraints": ["Recompute line extensions, subtotal, and total"],
        "source_expected_contract": {"outputs": "Invoice line items and arithmetic checks."},
    },
}
_SEMANTIC_KINDS = {
    "copy-editing": "copy_revision",
    "internal-comms": "indexed_facts",
    "contract-review": "quoted_risk_review",
    "note-taking": "source_referenced_notes",
    "invoice-processing": "invoice_arithmetic",
}


def _fixture_schema(value):
    if value is None:
        return {"type": "null"}
    if isinstance(value, bool):
        return {"type": "boolean"}
    if isinstance(value, int):
        return {"type": "integer"}
    if isinstance(value, float):
        return {"type": "number"}
    if isinstance(value, str):
        return {"type": "string"}
    if isinstance(value, list):
        return {
            "type": "array",
            "items": _fixture_schema(value[0]) if value else {},
        }
    if isinstance(value, dict):
        return {
            "type": "object",
            "additionalProperties": False,
            "properties": {name: _fixture_schema(item) for name, item in value.items()},
            "required": list(value),
        }
    raise AssertionError(f"unsupported fixture value: {type(value)!r}")


def _semantic_replay_runtime(tmp_path: Path, source_slug: str):
    replay = json.loads(SEMANTIC_REPLAY_PATH.read_text(encoding="utf-8"))
    inputs = json.loads(SEMANTIC_INPUTS_PATH.read_text(encoding="utf-8"))
    case = next(item for item in replay["cases"] if item["slug"] == source_slug)
    payload = inputs[source_slug]
    output = case["output"]
    assert compiler.sha256_text(
        json.dumps(output, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    ) == case["output_sha256"]
    assert compiler.sha256_text(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    ) == case["input_sha256"]

    business = {
        name: value for name, value in output.items() if name not in _WRAPPER_OUTPUT_FIELDS
    }
    profile = json.loads(PROFILE_PATH.read_text(encoding="utf-8"))
    structural_slug = "structural-" + source_slug
    profile["slug"] = structural_slug
    profile["name"] = structural_slug
    profile["input_schema"] = _fixture_schema(payload)
    profile["live"]["model_output_schema"] = _fixture_schema(business)
    profile["semantic_normalizers"] = {}
    profile["reviewed_spec"] = _SEMANTIC_PROMISES[source_slug]
    runtime_path = tmp_path / (structural_slug + ".py")
    runtime_path.write_text(compiler.modal_app_template(profile), encoding="utf-8")
    spec = importlib.util.spec_from_file_location(
        "generated_" + structural_slug.replace("-", "_"), runtime_path
    )
    assert spec is not None and spec.loader is not None
    runtime = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(runtime)
    assert runtime.SEMANTIC_EVIDENCE_SPEC["kind"] == _SEMANTIC_KINDS[source_slug]
    normalized = runtime._semantic_normalize(json.loads(json.dumps(output)), payload)
    return runtime, payload, normalized


def test_copy_revision_replays_recorded_good_output_with_contract_evidence(tmp_path: Path) -> None:
    runtime, payload, output = _semantic_replay_runtime(tmp_path, "copy-editing")
    assert runtime._semantic_validation_diff(output, payload) == ""
    output["unsupported_claims"] = ["No credit card required"]
    output["edits"].append({
        "after": "No credit card required",
        "before": "Choose the Team plan today.",
        "rationale": "A considered but unsupported risk reducer.",
        "sweep": "zero_risk",
    })
    runtime._semantic_normalize(output, payload)
    assert output["unsupported_claims"] == []
    assert all("No credit card required" not in item["after"] for item in output["edits"])
    assert runtime._semantic_validation_diff(output, payload) == ""
    output["revised_copy"] = payload["copy"]
    assert "semantic_revision_required" in runtime._semantic_validation_diff(output, payload)


def _hardening_semantic_runtime(tmp_path: Path, section: str):
    fixture = json.loads(HARDENING_FIXTURE_PATH.read_text(encoding="utf-8"))
    cases = fixture[section]
    profile = json.loads(PROFILE_PATH.read_text(encoding="utf-8"))
    profile["slug"] = "hardening-" + section.replace("_", "-")
    profile["name"] = profile["slug"]
    profile["input_schema"] = _fixture_schema(cases[0]["input"])
    profile["live"]["model_output_schema"] = _fixture_schema(
        cases[0]["semantic_projection"]
    )
    profile["semantic_normalizers"] = {}
    if section == "copy_editing":
        profile["reviewed_spec"] = {
            "constraints": [
                "Use only supplied facts",
                "Return a revised draft with before/after revision evidence",
            ],
            "source_expected_contract": {
                "outputs": "A revised draft and revision report."
            },
        }
        expected_kind = "copy_revision"
    else:
        profile["reviewed_spec"] = {
            "constraints": [
                "Reconcile every total from supplied arrays",
                "Variance equals actual minus budget",
            ],
            "source_expected_contract": {
                "outputs": "Budget totals, variances, percentages, and forecast."
            },
        }
        expected_kind = "budget_arithmetic"
    runtime_path = tmp_path / (profile["slug"] + ".py")
    runtime_path.write_text(compiler.modal_app_template(profile), encoding="utf-8")
    spec = importlib.util.spec_from_file_location(
        "generated_" + profile["slug"].replace("-", "_"), runtime_path
    )
    assert spec is not None and spec.loader is not None
    runtime = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(runtime)
    assert runtime.SEMANTIC_EVIDENCE_SPEC["kind"] == expected_kind
    return runtime, cases


def test_final_rerun_copy_fixtures_reconcile_claims_and_edit_pairs(
    tmp_path: Path,
) -> None:
    runtime, cases = _hardening_semantic_runtime(tmp_path, "copy_editing")
    assert runtime.SEMANTIC_EVIDENCE_SPEC["before_field"] == "before"
    for case in cases:
        payload = case["input"]
        assert compiler.sha256_text(
            json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        ) == case["input_sha256"]
        normalized = runtime._semantic_normalize(
            json.loads(json.dumps(case["semantic_projection"])), payload
        )
        assert runtime._semantic_validation_diff(normalized, payload) == ""
        if case["id"] == "reviewed-happy-path":
            assert normalized["unsupported_claims"] == []
            assert all(
                "No credit card required" not in item["after"]
                for item in normalized["edits"]
            )

    payload = cases[0]["input"]
    survives = json.loads(json.dumps(cases[0]["semantic_projection"]))
    survives["revised_copy"] += " No-credit-card required!"
    survives = runtime._semantic_normalize(survives, payload)
    assert "semantic_unsupported_claim" in runtime._semantic_validation_diff(
        survives, payload
    )

    missing_pair = runtime._semantic_normalize(
        json.loads(json.dumps(cases[1]["semantic_projection"])), cases[1]["input"]
    )
    missing_pair["edits"][0].pop("before")
    assert "semantic_before_after_pair_required" in runtime._semantic_validation_diff(
        missing_pair, cases[1]["input"]
    )

    shape_variant = json.loads(json.dumps(cases[0]["semantic_projection"]))
    shape_variant["unsupported_claims"] = [
        {"claim": "No credit card required", "reason": "absent from supplied facts"}
    ]
    shape_variant["edits"] = {
        "clarity": shape_variant["edits"][0],
        "zero_risk": shape_variant["edits"][1],
    }
    reconciled, shape_diff = runtime._candidate(
        json.dumps(shape_variant), cases[0]["input"]
    )
    assert shape_diff == ""
    assert reconciled is not None
    assert reconciled["unsupported_claims"] == []
    assert len(reconciled["edits"]) == 1


def test_final_rerun_budget_fixtures_allow_only_recomputed_derived_numbers(
    tmp_path: Path,
) -> None:
    runtime, cases = _hardening_semantic_runtime(tmp_path, "budget_planning")
    for case in cases:
        payload = case["input"]
        assert compiler.sha256_text(
            json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        ) == case["input_sha256"]
        output = json.loads(json.dumps(case["semantic_projection"]))
        assert runtime._semantic_validation_diff(output, payload) == ""

    wrong_target = json.loads(json.dumps(cases[1]["semantic_projection"]))
    wrong_target["target_variance"] = 200
    target_diff = runtime._semantic_validation_diff(wrong_target, cases[1]["input"])
    assert "$.target_variance:semantic_budget_arithmetic" in target_diff

    invented = json.loads(json.dumps(cases[1]["semantic_projection"]))
    invented["recommendations"] = ["Allocate 777 more next period."]
    assert "$:semantic_invented_number" in runtime._semantic_validation_diff(
        invented, cases[1]["input"]
    )


def test_indexed_facts_replays_recorded_paraphrases_with_valid_indexes(tmp_path: Path) -> None:
    runtime, payload, output = _semantic_replay_runtime(tmp_path, "internal-comms")
    assert runtime._semantic_validation_diff(output, payload) == ""
    output["fact_indexes_used"] = [len(payload["facts"])]
    assert "semantic_fact_index" in runtime._semantic_validation_diff(output, payload)


def test_quoted_risk_review_replays_disclaimer_wording_and_source_quotes(tmp_path: Path) -> None:
    runtime, payload, output = _semantic_replay_runtime(tmp_path, "contract-review")
    assert runtime._semantic_validation_diff(output, payload) == ""
    output["risks"][0]["source_quote"] = "language not present in the contract"
    assert "semantic_source_quote" in runtime._semantic_validation_diff(output, payload)


def test_source_referenced_notes_allow_normalized_dates_and_paraphrases(tmp_path: Path) -> None:
    runtime, payload, output = _semantic_replay_runtime(tmp_path, "note-taking")
    assert output["action_items"][0]["due_date"] == "2026-08-18"
    assert runtime._semantic_validation_diff(output, payload) == ""
    output["action_items"][0]["source_quote"] = "missing source sentence"
    assert "semantic_source_quote" in runtime._semantic_validation_diff(output, payload)


def test_invoice_arithmetic_replays_correct_values_despite_nullable_header_shape(tmp_path: Path) -> None:
    runtime, payload, output = _semantic_replay_runtime(tmp_path, "invoice-processing")
    assert output["due_date"] == ""
    assert output["po_reference"] == ""
    assert runtime._semantic_validation_diff(output, payload) == ""
    output["total"] = 71
    assert "semantic_invoice_total" in runtime._semantic_validation_diff(output, payload)


def test_structural_selector_preserves_grounded_copy_budget_and_education_classes() -> None:
    grounded_copy = {
        "input_schema": {"properties": {"product_name": {"type": "string"}}},
        "live": {"model_output_schema": {"properties": {
            "headline": {"type": "string"},
            "sections": {"type": "array"},
            "unsupported_claims": {"type": "array"},
        }}},
        "reviewed_spec": {"constraints": [
            "Use only supplied offer, proof, and differentiators",
            "Never fabricate statistics or testimonials",
        ]},
    }
    assert compiler.semantic_evidence_spec(grounded_copy)["kind"] == "grounded_copy"

    budget = {
        "input_schema": {"properties": {"lines": {
            "type": "array",
            "items": {"type": "object", "required": [
                "department", "category", "monthly_budget", "monthly_actual"
            ]},
        }}},
        "live": {"model_output_schema": {"properties": {
            "line_items": {
                "type": "array",
                "items": {"type": "object", "required": [
                    "department", "category", "budget_total", "actual_total", "variance_amount"
                ]},
            },
            "department_totals": {"type": "array"},
            "company_budget_total": {"type": "number"},
            "company_actual_total": {"type": "number"},
        }}},
        "reviewed_spec": {"constraints": [
            "Reconcile every total from supplied arrays",
            "Variance equals actual minus budget",
        ]},
    }
    assert compiler.semantic_evidence_spec(budget)["kind"] == "budget_arithmetic"

    education = json.loads(
        (ROOT / "packages" / "skill-to-modal" / "profiles" / "phonics-list-generator.json").read_text(
            encoding="utf-8"
        )
    )
    assert compiler.semantic_evidence_spec(education) == {
        "kind": "profile_semantic_normalizers",
        "normalizers": ["phoneme_containment"],
        "version": 1,
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
