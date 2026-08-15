#!/usr/bin/env python3
"""Provider-backed pre-deploy gate for one generated single-LLM workflow.

The command emits one sanitized JSON result. It never emits inputs, provider
outputs, prompts, response bodies, or environment values.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[2]
COMPILER_PATH = ROOT / "packages" / "skill-to-modal" / "compiler.py"
MAX_CASES = 3
MIN_CASES = 2
SAFE_BLOCKERS = {
    "SELF_TEST_CASES_INSUFFICIENT",
    "SELF_TEST_COMPILE_FAILED",
    "SELF_TEST_IMPORT_FAILED",
    "SELF_TEST_ENV_NOT_CONFIGURED",
    "SELF_TEST_PROVIDER_FAILED",
    "SELF_TEST_SCHEMA_FAILED",
    "SELF_TEST_SEMANTIC_FAILED",
    "SELF_TEST_INTERNAL_FAILED",
}
SAFE_SEMANTIC_CODES = {
    "COVERAGE_MISSING",
    "ECHO_MISMATCH",
    "INPUT_ITEM_MISSING",
    "LIST_COUNT_MISMATCH",
    "REQUESTED_COUNT_MISMATCH",
    "SPAN_MISMATCH",
}


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("expected JSON object")
    return value


def discover_cases(profile: dict[str, Any], external_cases: list[Any] | None = None) -> list[dict[str, Any]]:
    candidates: list[Any] = list(external_cases or [])
    self_test = profile.get("self_test")
    if isinstance(self_test, dict):
        candidates.extend(self_test.get("cases") or [])
    marketplace = profile.get("marketplace")
    if isinstance(marketplace, dict):
        candidates.extend(marketplace.get("examples") or [])
    candidates.append(profile.get("happy_path") or {})
    validator = Draft202012Validator(profile["input_schema"])
    unique: list[dict[str, Any]] = []
    seen: set[str] = set()
    for candidate in candidates:
        value = candidate.get("input") if isinstance(candidate, dict) else None
        if not isinstance(value, dict) or list(validator.iter_errors(value)):
            continue
        marker = _canonical(value)
        if marker in seen:
            continue
        seen.add(marker)
        unique.append(value)
        if len(unique) == MAX_CASES:
            break
    return unique


def semantic_issues(payload: dict[str, Any], output: dict[str, Any]) -> list[str]:
    issues: set[str] = set()
    for key in ("word", "dialect"):
        if key in payload and key in output and output[key] != payload[key]:
            issues.add("ECHO_MISMATCH")
    if "text" in payload and "input" in output and output["input"] != payload["text"]:
        issues.add("ECHO_MISMATCH")

    count_pairs = {
        "num_sentences": "sentences",
        "word_count": "words",
        "num_examples": "examples",
        "num_ideas": "ideas",
    }
    for input_key, output_key in count_pairs.items():
        if input_key in payload and isinstance(output.get(output_key), list):
            if len(output[output_key]) != payload[input_key]:
                issues.add("REQUESTED_COUNT_MISMATCH")

    for key, value in output.items():
        if not key.endswith("_count") or not isinstance(value, int):
            continue
        stem = key.removesuffix("_count")
        for sibling, items in output.items():
            singular = sibling[:-1] if sibling.endswith("s") else sibling
            if singular == stem and isinstance(items, list) and len(items) != value:
                issues.add("LIST_COUNT_MISMATCH")

    coverage = output.get("coverage")
    requested = payload.get("phonemes") or payload.get("phonics_patterns")
    if isinstance(coverage, list) and isinstance(requested, list):
        normalized = {str(item).strip().lower() for item in coverage}
        if any(str(item).strip().lower() not in normalized for item in requested):
            issues.add("COVERAGE_MISSING")

    source_text = payload.get("text")
    occurrences = output.get("occurrences")
    if isinstance(source_text, str) and isinstance(occurrences, list):
        for item in occurrences:
            if not isinstance(item, dict):
                issues.add("SPAN_MISMATCH")
                continue
            start, end, text = item.get("start"), item.get("end"), item.get("text")
            if (
                not isinstance(start, int)
                or isinstance(start, bool)
                or not isinstance(end, int)
                or isinstance(end, bool)
                or start < 0
                or end <= start
                or source_text[start:end].lower() != str(text).lower()
            ):
                issues.add("SPAN_MISMATCH")

    input_words = payload.get("words")
    output_items = output.get("items")
    if isinstance(input_words, list) and isinstance(output_items, list):
        returned = [item.get("word") for item in output_items if isinstance(item, dict)]
        if returned != input_words:
            issues.add("INPUT_ITEM_MISSING")
    return sorted(issues)


def _load_runtime(path: Path) -> Any:
    module_name = "omo_one_shot_" + re.sub(r"[^a-z0-9_]", "_", path.parent.name.lower())
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError("runtime import failed")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run_self_test(
    skill_path: Path,
    profile_path: Path,
    out: Path,
    *,
    external_cases: list[Any] | None = None,
) -> dict[str, Any]:
    profile = _load_json(profile_path)
    cases = discover_cases(profile, external_cases)
    if len(cases) < MIN_CASES:
        return {"status": "blocked", "blocker": "SELF_TEST_CASES_INSUFFICIENT", "cases": len(cases)}
    command = [
        sys.executable,
        str(COMPILER_PATH),
        str(skill_path),
        "--profile",
        str(profile_path),
        "--out",
        str(out),
    ]
    compiled = subprocess.run(
        command,
        cwd=ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        timeout=120,
        check=False,
    )
    if compiled.returncode != 0:
        return {"status": "blocked", "blocker": "SELF_TEST_COMPILE_FAILED", "cases": len(cases)}
    try:
        runtime = _load_runtime(out / "modal_app.py")
    except Exception:
        return {"status": "blocked", "blocker": "SELF_TEST_IMPORT_FAILED", "cases": len(cases)}

    semantic_failures = 0
    for payload in cases:
        try:
            result = runtime.execute_workflow(payload)
        except getattr(runtime, "WorkflowNotReady", RuntimeError):
            return {"status": "blocked", "blocker": "SELF_TEST_ENV_NOT_CONFIGURED", "cases": len(cases)}
        except getattr(runtime, "ProviderCallError", RuntimeError):
            return {"status": "blocked", "blocker": "SELF_TEST_PROVIDER_FAILED", "cases": len(cases)}
        except Exception:
            return {"status": "blocked", "blocker": "SELF_TEST_SCHEMA_FAILED", "cases": len(cases)}
        issues = semantic_issues(payload, result)
        if any(issue not in SAFE_SEMANTIC_CODES for issue in issues):
            return {"status": "blocked", "blocker": "SELF_TEST_INTERNAL_FAILED", "cases": len(cases)}
        if issues:
            semantic_failures += 1
    passed = len(cases) - semantic_failures
    if semantic_failures:
        return {
            "status": "blocked",
            "blocker": "SELF_TEST_SEMANTIC_FAILED",
            "cases": len(cases),
            "passed": passed,
        }
    return {"status": "passed", "cases": len(cases), "passed": passed}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true", required=True)
    parser.add_argument("--skill", type=Path, required=True)
    parser.add_argument("--profile", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--cases", type=Path)
    parser.add_argument("--result-file", type=Path)
    return parser.parse_args()


def write_safe_result(path: Path, result: dict[str, Any]) -> None:
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        handle.write(json.dumps(result, sort_keys=True) + "\n")


def main() -> int:
    args = parse_args()
    external: list[Any] | None = None
    try:
        if args.cases:
            loaded = json.loads(args.cases.read_text(encoding="utf-8"))
            external = loaded if isinstance(loaded, list) else None
        result = run_self_test(
            args.skill.resolve(),
            args.profile.resolve(),
            args.out.resolve(),
            external_cases=external,
        )
    except Exception:
        result = {"status": "blocked", "blocker": "SELF_TEST_INTERNAL_FAILED", "cases": 0}
    if result.get("blocker") not in SAFE_BLOCKERS | {None}:
        result = {"status": "blocked", "blocker": "SELF_TEST_INTERNAL_FAILED", "cases": 0}
    if args.result_file:
        try:
            write_safe_result(args.result_file.resolve(), result)
        except Exception:
            result = {"status": "blocked", "blocker": "SELF_TEST_INTERNAL_FAILED", "cases": 0}
    print(json.dumps(result, sort_keys=True))
    return 0 if result["status"] == "passed" else 2


if __name__ == "__main__":
    raise SystemExit(main())
