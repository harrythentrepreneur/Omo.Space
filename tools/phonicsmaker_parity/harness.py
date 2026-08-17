"""Strict, offline PhonicsMaker-to-Omo parity comparisons."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


OUTPUT_TRANSPORT_KEYS = frozenset({"run_id", "status", "workflow_version", "usage"})
ARTIFACT_TRANSPORT_KEYS = frozenset({"object_key", "url", "download_url", "signed_url"})


@dataclass(frozen=True)
class ParityReport:
    """Comparison result suitable for JSON serialization."""

    mismatches: list[dict[str, Any]]

    @property
    def passed(self) -> bool:
        return not self.mismatches

    def to_dict(self) -> dict[str, Any]:
        return {"passed": self.passed, "mismatches": self.mismatches}


def _path(parent: str, child: str | int) -> str:
    if isinstance(child, int):
        return f"{parent}[{child}]"
    return f"{parent}.{child}" if parent != "$" else f"$.{child}"


def _diff(source: Any, candidate: Any, path: str, kind: str, out: list[dict[str, Any]]) -> None:
    if isinstance(source, dict) and isinstance(candidate, dict):
        for key in sorted(source.keys() - candidate.keys()):
            out.append({"kind": kind, "path": _path(path, key), "reason": "missing_in_omo", "source": source[key]})
        for key in sorted(candidate.keys() - source.keys()):
            out.append({"kind": kind, "path": _path(path, key), "reason": "extra_in_omo", "candidate": candidate[key]})
        for key in sorted(source.keys() & candidate.keys()):
            _diff(source[key], candidate[key], _path(path, key), kind, out)
        return

    if isinstance(source, list) and isinstance(candidate, list):
        if len(source) != len(candidate):
            out.append({
                "kind": kind,
                "path": path,
                "reason": "length_mismatch",
                "source_length": len(source),
                "candidate_length": len(candidate),
            })
        for index in range(min(len(source), len(candidate))):
            _diff(source[index], candidate[index], _path(path, index), kind, out)
        return

    if source != candidate or type(source) is not type(candidate):
        out.append({"kind": kind, "path": path, "reason": "value_mismatch", "source": source, "candidate": candidate})


def _without_keys(value: Any, ignored: frozenset[str]) -> Any:
    if isinstance(value, dict):
        return {key: _without_keys(item, ignored) for key, item in value.items() if key not in ignored}
    if isinstance(value, list):
        return [_without_keys(item, ignored) for item in value]
    return value


def _canonical_artifacts(value: Any) -> Any:
    if not isinstance(value, list):
        return value
    canonical = []
    for artifact in value:
        if isinstance(artifact, dict):
            canonical.append(_without_keys(artifact, ARTIFACT_TRANSPORT_KEYS))
        else:
            canonical.append(artifact)
    return canonical


def compare_case(source_case: dict[str, Any], omo_case: dict[str, Any]) -> ParityReport:
    """Compare one sanitized source/Omo fixture pair.

    Inputs are exact. Logical outputs are exact after removing only Omo's
    transport envelope fields. Artifact content metadata and hashes are exact;
    only private delivery identifiers/URLs are transport-owned and ignored.
    """

    mismatches: list[dict[str, Any]] = []
    _diff(source_case.get("input", {}), omo_case.get("input", {}), "$.input", "input", mismatches)

    source_output = _without_keys(source_case.get("output", {}), OUTPUT_TRANSPORT_KEYS)
    omo_output = _without_keys(omo_case.get("output", {}), OUTPUT_TRANSPORT_KEYS)
    _diff(source_output, omo_output, "$.output", "output", mismatches)

    source_artifacts = _canonical_artifacts(source_case.get("artifacts", []))
    omo_artifacts = _canonical_artifacts(omo_case.get("artifacts", []))
    _diff(source_artifacts, omo_artifacts, "$.artifacts", "artifact", mismatches)
    return ParityReport(mismatches)


def compare_contracts(source_contract: dict[str, Any], omo_contract: dict[str, Any]) -> ParityReport:
    """Compare input/output contract snapshots with no transport exemptions."""

    mismatches: list[dict[str, Any]] = []
    _diff(source_contract, omo_contract, "$", "contract", mismatches)
    return ParityReport(mismatches)
