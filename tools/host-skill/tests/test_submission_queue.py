"""Creator submission intake and review-gate tests."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[3]
MODULE_PATH = ROOT / "tools" / "host-skill" / "submission_queue.py"


def load_module():
    spec = importlib.util.spec_from_file_location("submission_queue_test", MODULE_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


queue = load_module()


def sample(name: str = "sample-workflow", description: str = "A safe sample workflow.") -> str:
    return f"---\nname: {name}\ndescription: {description}\n---\n\n## Workflow\n\n1. **Read:** Read the supplied brief.\n"


def test_valid_submission_derives_server_metadata() -> None:
    validated = queue.validate_submission("Sample Workflow", sample())
    assert validated.name == "sample-workflow"
    assert validated.slug == "sample-workflow"
    assert validated.source_sha256
    assert validated.size_bytes == len(sample().encode("utf-8"))


@pytest.mark.parametrize(
    "name,content,code",
    [
        ("", sample(), "name_required"),
        ("different", sample(), "name_mismatch"),
        ("sample-workflow", "# no frontmatter", "invalid_frontmatter"),
        ("sample-workflow", "---\nname: sample-workflow\n---\n", "invalid_frontmatter"),
        ("sample-workflow", sample() + "\x00", "invalid_content"),
    ],
)
def test_invalid_submissions_fail_with_stable_codes(name: str, content: str, code: str) -> None:
    with pytest.raises(queue.SubmissionValidationError) as captured:
        queue.validate_submission(name, content)
    assert captured.value.code == code


def test_utf8_byte_limit_not_character_count() -> None:
    base = sample()
    within = base + "é" * ((queue.MAX_SUBMISSION_BYTES - len(base.encode("utf-8"))) // 2)
    assert queue.validate_submission("sample-workflow", within).size_bytes <= queue.MAX_SUBMISSION_BYTES
    with pytest.raises(queue.SubmissionValidationError) as captured:
        queue.validate_submission("sample-workflow", within + "é")
    assert captured.value.code == "content_too_large"


def test_unknown_sample_stops_for_profile_review(tmp_path: Path) -> None:
    validated = queue.validate_submission("sample-workflow", sample())
    state, reason = queue.evaluate_review_gate(validated, tmp_path)
    assert (state, reason) == ("needs_review", "reviewed_profile_required")


def test_slug_collision_stops_before_profile_or_build(tmp_path: Path) -> None:
    validated = queue.validate_submission("sample-workflow", sample())
    collision = tmp_path / "containers" / validated.slug
    collision.mkdir(parents=True)
    state, reason = queue.evaluate_review_gate(validated, tmp_path)
    assert (state, reason) == ("needs_review", "slug_collision")


def test_ready_submission_can_resume_only_its_matching_generated_container(tmp_path: Path) -> None:
    validated = queue.validate_submission("sample-workflow", sample())
    source = tmp_path / "containers" / validated.slug / "source" / "SKILL.md"
    source.parent.mkdir(parents=True)
    source.write_text(validated.content, encoding="utf-8")
    profile_path = tmp_path / "packages" / "skill-to-modal" / "profiles" / "sample-workflow.json"
    profile_path.parent.mkdir(parents=True)
    profile_path.write_text(json.dumps({"name": validated.name, "slug": validated.slug}), encoding="utf-8")
    assert queue.evaluate_review_gate(validated, tmp_path) == ("needs_review", "slug_collision")
    assert queue.evaluate_review_gate(validated, tmp_path, allow_matching_container=True) == ("ready_for_build", None)


def test_collision_resume_requires_matching_package_and_container_sources(tmp_path: Path) -> None:
    validated = queue.validate_submission("sample-workflow", sample())
    container_source = tmp_path / "containers" / validated.slug / "source" / "SKILL.md"
    package_source = tmp_path / "packages" / validated.slug / "SKILL.md"
    profile_path = tmp_path / "packages" / "skill-to-modal" / "profiles" / "sample-workflow.json"
    container_source.parent.mkdir(parents=True)
    package_source.parent.mkdir(parents=True)
    profile_path.parent.mkdir(parents=True)
    container_source.write_bytes(validated.content.encode("utf-8"))
    package_source.write_bytes(b"different reviewed package bytes")
    profile_path.write_text(json.dumps({"name": validated.name, "slug": validated.slug}), encoding="utf-8")

    assert queue.evaluate_review_gate(validated, tmp_path, allow_matching_container=True) == ("needs_review", "slug_collision")

    package_source.write_bytes(validated.content.encode("utf-8"))
    assert queue.evaluate_review_gate(validated, tmp_path, allow_matching_container=True) == ("ready_for_build", None)


def test_matching_reviewed_profile_can_build(tmp_path: Path) -> None:
    validated = queue.validate_submission("sample-workflow", sample())
    profile_path = tmp_path / "packages" / "skill-to-modal" / "profiles" / "sample-workflow.json"
    profile_path.parent.mkdir(parents=True)
    profile_path.write_text(json.dumps({"name": validated.name, "slug": validated.slug}), encoding="utf-8")
    assert queue.evaluate_review_gate(validated, tmp_path) == ("ready_for_build", None)
