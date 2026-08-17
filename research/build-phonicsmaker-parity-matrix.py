#!/usr/bin/env python3
"""Build a source-to-Omo parity matrix without touching secrets or production.

The matrix is deliberately conservative: an Omo profile/container match is only
"candidate-hosted-unverified". It is never treated as parity until a differential
fixture and artifact-quality gate exists.
"""
from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
WEB = Path("/root/work/phonicsmaker/web")
CORE = Path("/root/work/phonicsmaker/core")
PROFILES = ROOT / "packages/skill-to-modal/profiles"
CONTAINERS = ROOT / "containers"
OUT = ROOT / "research/phonicsmaker-parity-matrix.json"
EXCLUDED_PARTS = {".git", ".venv", "node_modules", ".next", "__pycache__", ".pytest_cache"}


def git_head(repo: Path) -> dict[str, str]:
    def run(*args: str) -> str:
        return subprocess.check_output(["git", "-C", str(repo), *args], text=True).strip()

    return {
        "branch": run("branch", "--show-current"),
        "head": run("rev-parse", "HEAD"),
        "origin_main": run("rev-parse", "origin/main"),
    }


def exists(path: Path) -> bool:
    return path.exists()


def source_files(root: Path, pattern: str) -> list[str]:
    return sorted(
        str(path.relative_to(root))
        for path in root.rglob(pattern)
        if not any(part in EXCLUDED_PARTS for part in path.parts)
    )


def object_keys(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8", errors="ignore")
    return sorted(
        set(re.findall(r"^\s*['\"]([^'\"]+)['\"]\s*:\s*\{", text, flags=re.MULTILINE))
    )


def file_stems(root: Path) -> set[str]:
    return {
        path.stem
        for path in root.glob("*.json")
        if path.is_file() and path.name != "package.json"
    }


def container_names(root: Path) -> set[str]:
    return {
        path.name
        for path in root.iterdir()
        if path.is_dir() and not path.name.startswith(".")
    }


def hosting_status(slug: str, profiles: set[str], containers: set[str]) -> dict[str, Any]:
    profile = slug in profiles
    container = slug in containers
    if profile and container:
        status = "candidate-hosted-unverified"
    elif profile or container:
        status = "partial-hosting-scaffold"
    else:
        status = "missing-hosting-scaffold"
    return {
        "omo_slug": slug,
        "omo_profile": profile,
        "omo_container": container,
        "status": status,
        "parity_proven": False,
    }


def make_tool_rows() -> list[dict[str, Any]]:
    prompts = object_keys(WEB / "src/app/api/tools/prompts.ts")
    configured = object_keys(WEB / "src/shared/toolConfig.ts")
    profiles = file_stems(PROFILES)
    containers = container_names(CONTAINERS)
    rows: list[dict[str, Any]] = []

    for slug in configured:
        row = {
            "id": f"tool:{slug}",
            "source_kind": "configured_tool",
            "source_ref": "web/src/shared/toolConfig.ts",
            "slug": slug,
            "source_present": True,
            "source_has_prompt": slug in prompts,
        }
        row.update(hosting_status(slug, profiles, containers))
        rows.append(row)

    for slug in sorted(set(prompts) - set(configured)):
        row = {
            "id": f"prompt:{slug}",
            "source_kind": "prompt_only_tool",
            "source_ref": "web/src/app/api/tools/prompts.ts",
            "slug": slug,
            "source_present": True,
            "source_has_prompt": True,
        }
        row.update(hosting_status(slug, profiles, containers))
        rows.append(row)
    return rows


def make_core_rows() -> list[dict[str, Any]]:
    features = [
        ("core:story-generation", "story_generation", ["app/phonics_maker/story_generation", "app/phonics_maker/tasks/story_tasks.py"], "illustrated-decodable-story-maker"),
        ("core:image-generation", "image_generation", ["app/phonics_maker/image_generation"], "illustrated-decodable-story-maker"),
        ("core:worksheet-generation", "worksheet_generation", ["app/phonics_maker/worksheet_generation"], "phonics-worksheet-generator"),
        ("core:activity-generation", "activity_generation", ["app/phonics_maker/activity_generation"], "illustrated-decodable-story-maker"),
        ("core:audio-generation", "audio_generation", ["app/phonics_maker/audio_generation"], "phonics-audio-narration"),
        ("core:pdf-rendering", "pdf_generation", ["app/phonics_maker/pdf_generation", "templates"], "illustrated-decodable-story-maker"),
        ("core:pptx-export", "pptx_export", ["app/phonics_maker/pdf_generation/pptx_generator.py"], "phonics-pptx-export"),
        ("core:task-management", "task_management", ["app/phonics_maker/task_management", "app/phonics_maker/tasks"], "phonicsmaker-task-runtime"),
        ("core:storage", "artifact_storage", ["app/core/storage/file_storage.py"], "phonicsmaker-artifact-plane"),
    ]
    profiles = file_stems(PROFILES)
    containers = container_names(CONTAINERS)
    rows: list[dict[str, Any]] = []
    for row_id, capability, refs, slug in features:
        present_refs = [ref for ref in refs if exists(CORE / ref)]
        row = {
            "id": row_id,
            "source_kind": "core_runtime_capability",
            "source_ref": present_refs,
            "capability": capability,
            "source_present": bool(present_refs),
        }
        row.update(hosting_status(slug, profiles, containers))
        rows.append(row)
    return rows


def make_journey_rows() -> list[dict[str, Any]]:
    journeys = [
        ("journey:worksheet-generator", "web/src/app/[lang]/dashboard/worksheet-generator", "phonics-worksheet-generator"),
        ("journey:toolkit", "web/src/app/[lang]/dashboard/toolkit", "tool-suite"),
        ("journey:book-sets", "web/src/app/[lang]/dashboard/book-sets", "decodable-book-maker"),
        ("journey:edit-studio", "web/src/app/[lang]/dashboard/studio", "phonics-story-edit-studio"),
        ("journey:storybook-editor", "web/src/app/[lang]/dashboard/storybook-editor", "phonics-story-edit-studio"),
        ("journey:phonics-games", "web/src/app/[lang]/dashboard/phonicgames", "phonics-games"),
        ("journey:dictation", "web/src/app/[lang]/dashboard/dictation", "phonics-dictation"),
        ("journey:high-frequency-words", "web/src/app/[lang]/dashboard/highfrequencywords", "high-frequency-words"),
        ("journey:syllable-builder", "web/src/app/[lang]/dashboard/syllablebuilder", "syllable-splitter-and-counter"),
        ("journey:journal", "web/src/app/[lang]/dashboard/journal", "phonics-journal"),
        ("journey:listening", "web/src/app/listen", "phonics-audio-narration"),
        ("journey:curricula", "web/src/app/[lang]/dashboard/worksheet-generator/curricula", "phonics-curriculum"),
    ]
    profiles = file_stems(PROFILES)
    containers = container_names(CONTAINERS)
    rows: list[dict[str, Any]] = []
    for row_id, ref, slug in journeys:
        row = {
            "id": row_id,
            "source_kind": "web_product_journey",
            "source_ref": ref,
            "source_present": exists(WEB / ref),
        }
        row.update(hosting_status(slug, profiles, containers))
        rows.append(row)
    return rows


def main() -> None:
    rows = make_tool_rows() + make_core_rows() + make_journey_rows()
    counts: dict[str, int] = {}
    for row in rows:
        counts[row["status"]] = counts.get(row["status"], 0) + 1
    output = {
        "generated_by": str(Path(__file__).relative_to(ROOT)),
        "source_snapshots": {"web": git_head(WEB), "core": git_head(CORE)},
        "omo_snapshot": {
            "profiles": sorted(file_stems(PROFILES)),
            "containers": sorted(container_names(CONTAINERS)),
        },
        "rules": {
            "candidate_hosted_is_not_parity": True,
            "parity_proven_requires_differential_fixture_and_quality_gates": True,
            "production_status_is_not_inferred_from_local_files": True,
        },
        "counts_by_status": counts,
        "rows": rows,
    }
    OUT.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(OUT), "row_count": len(rows), "counts_by_status": counts}, indent=2))


if __name__ == "__main__":
    main()
