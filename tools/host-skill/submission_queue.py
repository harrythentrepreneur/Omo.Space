#!/usr/bin/env python3
"""Validation and queue helpers for creator-submitted workflow Markdown.

Uploaded Markdown is data, never executable input.  This module deliberately
shares the reviewed compiler's parser, but adds the intake limits enforced by
the Worker so agent-side processing cannot accidentally accept a looser shape.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
COMPILER_PATH = ROOT / "packages" / "skill-to-modal" / "compiler.py"
PROFILE_ROOT = ROOT / "packages" / "skill-to-modal" / "profiles"
CONTAINER_ROOT = ROOT / "containers"
MAX_SUBMISSION_BYTES = 200 * 1024
MAX_NAME_LENGTH = 120
MAX_DESCRIPTION_LENGTH = 500
SUBMISSION_ID_RE = re.compile(r"^sub_[A-Za-z0-9_-]{8,100}$")
SAFE_FAILURE_RE = re.compile(r"^[a-z][a-z0-9_]{2,63}$")


def _load_compiler() -> Any:
    spec = importlib.util.spec_from_file_location("omo_submission_compiler", COMPILER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("could not load the reviewed skill compiler")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


COMPILER = _load_compiler()


class SubmissionValidationError(ValueError):
    """A stable, non-secret creator intake failure."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class ValidatedSubmission:
    name: str
    description: str
    slug: str
    content: str
    source_sha256: str
    size_bytes: int


def validate_submission(name: Any, content: Any) -> ValidatedSubmission:
    """Validate the exact public intake contract and derive trusted metadata."""

    if not isinstance(content, str) or not content.strip():
        raise SubmissionValidationError("content_required", "Paste or upload workflow Markdown.")
    if "\x00" in content:
        raise SubmissionValidationError("invalid_content", "Workflow Markdown cannot contain NUL bytes.")
    size_bytes = len(content.encode("utf-8"))
    if size_bytes > MAX_SUBMISSION_BYTES:
        raise SubmissionValidationError(
            "content_too_large", f"Workflow Markdown must be {MAX_SUBMISSION_BYTES} bytes or smaller."
        )

    supplied_name = str(name or "").strip()
    if not supplied_name:
        raise SubmissionValidationError("name_required", "Give the workflow a name.")
    if len(supplied_name) > MAX_NAME_LENGTH:
        raise SubmissionValidationError("name_too_long", f"Workflow names allow {MAX_NAME_LENGTH} characters.")

    try:
        parsed = COMPILER.parse_skill(content)
    except ValueError as error:
        raise SubmissionValidationError("invalid_frontmatter", str(error)) from error

    canonical_name = parsed["name"].strip()
    description = parsed["description"].strip()
    if len(canonical_name) > MAX_NAME_LENGTH:
        raise SubmissionValidationError("name_too_long", f"Frontmatter names allow {MAX_NAME_LENGTH} characters.")
    if len(description) > MAX_DESCRIPTION_LENGTH:
        raise SubmissionValidationError(
            "description_too_long", f"Frontmatter descriptions allow {MAX_DESCRIPTION_LENGTH} characters."
        )
    if COMPILER.slugify(supplied_name) != parsed["slug"]:
        raise SubmissionValidationError(
            "name_mismatch", "Workflow name must match the name in Markdown frontmatter."
        )
    slug = parsed["slug"]
    if len(slug) > 100:
        raise SubmissionValidationError("slug_too_long", "The name produces a slug longer than 100 characters.")

    return ValidatedSubmission(
        name=canonical_name,
        description=description,
        slug=slug,
        content=content,
        source_sha256=hashlib.sha256(content.encode("utf-8")).hexdigest(),
        size_bytes=size_bytes,
    )


def evaluate_review_gate(
    validated: ValidatedSubmission, root: Path = ROOT, allow_matching_container: bool = False
) -> tuple[str, str | None]:
    """Return the next safe queue state without modifying the repository."""

    profile_path = root / "packages" / "skill-to-modal" / "profiles" / f"{validated.slug}.json"
    container_path = root / "containers" / validated.slug
    package_path = root / "packages" / validated.slug / "SKILL.md"

    expected_source = validated.content.encode("utf-8")
    matching_generated_source = container_path / "source" / "SKILL.md"
    container_is_owned_resume = allow_matching_container and matching_generated_source.is_file()
    package_is_owned_resume = False
    if container_is_owned_resume:
        try:
            container_is_owned_resume = matching_generated_source.read_bytes() == expected_source
            package_is_owned_resume = not package_path.exists() or (
                package_path.is_file() and package_path.read_bytes() == expected_source
            )
        except OSError:
            container_is_owned_resume = False
            package_is_owned_resume = False
    if (package_path.exists() and not package_is_owned_resume) or (container_path.exists() and not container_is_owned_resume):
        return "needs_review", "slug_collision"
    if not profile_path.is_file():
        return "needs_review", "reviewed_profile_required"

    try:
        profile = json.loads(profile_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return "failed", "invalid_reviewed_profile"
    if profile.get("slug") != validated.slug or profile.get("name") != validated.name:
        return "failed", "profile_identity_mismatch"
    return "ready_for_build", None


def safe_failure_code(value: str) -> str:
    code = str(value or "internal_error").strip().lower()
    return code if SAFE_FAILURE_RE.fullmatch(code) else "internal_error"


def validate_submission_id(value: str) -> str:
    submission_id = str(value or "").strip()
    if not SUBMISSION_ID_RE.fullmatch(submission_id):
        raise ValueError("submission id must start with sub_ and contain only URL-safe characters")
    return submission_id
