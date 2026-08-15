"""Strict launch adapter for the isolated Omo Hermes builder on Modal."""
from __future__ import annotations

import hashlib
import os
import re
from typing import Any, Mapping

ID_RE = re.compile(r"^sub_[A-Za-z0-9_-]{8,100}$")
SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
SHA_RE = re.compile(r"^[0-9a-f]{64}$")
DISPATCH_RE = re.compile(r"^dispatch_[0-9a-f]{32}$")
REVISION_RE = re.compile(r"^[0-9a-f]{40}$")
DEFAULT_APP = "omo-hermes-builder"
DEFAULT_FUNCTION = "build_submission"


def dispatch_id_for(submission_id: str, source_sha256: str, base_revision: str) -> str:
    if not ID_RE.fullmatch(str(submission_id)) or not SHA_RE.fullmatch(str(source_sha256)) or not REVISION_RE.fullmatch(str(base_revision)):
        raise ValueError("invalid builder dispatch identity")
    digest = hashlib.sha256(f"omo-modal-builder-v2\0{submission_id}\0{source_sha256}\0{base_revision}".encode()).hexdigest()
    return "dispatch_" + digest[:32]


def launch_modal_builder(
    *,
    submission_id: str,
    slug: str,
    source_sha256: str,
    dispatch_id: str,
    base_revision: str,
    environ: Mapping[str, str] | None = None,
) -> dict[str, str]:
    """Spawn one deployed Modal builder function with identifiers only."""
    env = environ or os.environ
    if (
        not ID_RE.fullmatch(str(submission_id))
        or not SLUG_RE.fullmatch(str(slug))
        or not SHA_RE.fullmatch(str(source_sha256))
        or not DISPATCH_RE.fullmatch(str(dispatch_id))
        or not REVISION_RE.fullmatch(str(base_revision))
        or dispatch_id != dispatch_id_for(submission_id, source_sha256, base_revision)
    ):
        raise ValueError("invalid builder launch payload")

    app_name = str(env.get("OMO_MODAL_BUILDER_APP", DEFAULT_APP)).strip()
    function_name = str(env.get("OMO_MODAL_BUILDER_FUNCTION", DEFAULT_FUNCTION)).strip()
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", app_name):
        raise ValueError("invalid Modal builder app name")
    if not re.fullmatch(r"[a-z][a-z0-9_]{1,63}", function_name):
        raise ValueError("invalid Modal builder function name")

    import modal

    function = modal.Function.from_name(app_name, function_name)
    call: Any = function.spawn(submission_id, slug, source_sha256, dispatch_id, base_revision)
    call_id = str(getattr(call, "object_id", "") or "")
    if not call_id:
        raise RuntimeError("Modal builder spawn returned no call id")
    return {"call_id": call_id, "dispatch_id": dispatch_id}
