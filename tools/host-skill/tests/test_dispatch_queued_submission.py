from __future__ import annotations
import hashlib
import importlib.util
import json
import stat
from pathlib import Path
from types import SimpleNamespace

SCRIPT = Path(__file__).resolve().parents[1] / "automation" / "dispatch-queued-submission.py"

def load_dispatch():
    spec = importlib.util.spec_from_file_location("omo_dispatch", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def setup_env(monkeypatch, tmp_path: Path) -> Path:
    root = tmp_path / "reviews"
    root.mkdir(mode=0o700)
    monkeypatch.setenv("OMO_BUILD_REVIEW_ROOT", str(root))
    monkeypatch.setenv("OMO_BUILDER_LOCK", str(tmp_path / "dispatch.lock"))
    return root

def test_idle_claim_starts_no_agent(monkeypatch, tmp_path: Path, capsys) -> None:
    dispatch = load_dispatch()
    setup_env(monkeypatch, tmp_path)
    calls = []
    def fake_run(command, **kwargs):
        calls.append(command)
        return SimpleNamespace(returncode=0, stdout=json.dumps({"status": "idle", "message": "No queued submission."}) + "\n")
    monkeypatch.setattr(dispatch.subprocess, "run", fake_run)
    assert dispatch.run_once() == 0
    assert len(calls) == 1
    assert "process-submissions.py" in calls[0][-1]
    assert capsys.readouterr().out == ""

def test_valid_private_review_starts_builder_once_without_source_in_prompt(monkeypatch, tmp_path: Path, capsys) -> None:
    dispatch = load_dispatch()
    root = setup_env(monkeypatch, tmp_path)
    source = b"untrusted creator source SECRET_SENTINEL"
    submission_id = "sub_abcdefgh12345678"
    review_dir = root / submission_id
    review_dir.mkdir(mode=0o700)
    review = review_dir / "SKILL.md"
    review.write_bytes(source)
    review.chmod(0o600)
    digest = hashlib.sha256(source).hexdigest()
    result = {"id": submission_id, "slug": "safe-skill", "status": "needs_review", "failure_code": "reviewed_profile_required", "source_sha256": digest, "review_path": str(review)}
    calls = []
    def fake_run(command, **kwargs):
        calls.append(command)
        if len(calls) == 1:
            return SimpleNamespace(returncode=0, stdout=json.dumps(result) + "\n")
        return SimpleNamespace(returncode=0, stdout="")
    monkeypatch.setattr(dispatch.subprocess, "run", fake_run)
    assert dispatch.run_once() == 0
    assert len(calls) == 2
    assert calls[1][:5] == ["hermes", "-p", "omo-builder", "chat", "-q"]
    prompt = calls[1][5]
    assert str(review) in prompt and digest in prompt
    assert "SECRET_SENTINEL" not in prompt
    assert "SECRET_SENTINEL" not in capsys.readouterr().out
    assert stat.S_IMODE(review.stat().st_mode) == 0o600

def test_malformed_claim_cannot_inject_builder_arguments(monkeypatch, tmp_path: Path) -> None:
    dispatch = load_dispatch()
    setup_env(monkeypatch, tmp_path)
    result = {"id": "sub_goodvalue;touch-pwn", "slug": "safe", "status": "needs_review", "failure_code": "reviewed_profile_required", "source_sha256": "a" * 64, "review_path": "/tmp/nope"}
    calls = []
    def fake_run(command, **kwargs):
        calls.append(command)
        return SimpleNamespace(returncode=0, stdout=json.dumps(result) + "\n")
    monkeypatch.setattr(dispatch.subprocess, "run", fake_run)
    assert dispatch.run_once() == 1
    assert len(calls) == 1

def test_non_review_status_does_not_start_agent(monkeypatch, tmp_path: Path) -> None:
    dispatch = load_dispatch()
    setup_env(monkeypatch, tmp_path)
    result = {"id": "sub_abcdefgh12345678", "slug": "safe-skill", "status": "ready_for_deploy", "failure_code": None}
    calls = []
    def fake_run(command, **kwargs):
        calls.append(command)
        return SimpleNamespace(returncode=0, stdout=json.dumps(result) + "\n")
    monkeypatch.setattr(dispatch.subprocess, "run", fake_run)
    assert dispatch.run_once() == 0
    assert len(calls) == 1
