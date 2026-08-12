import asyncio
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
CLI = ROOT / "tools/skill-to-modal/compiler.py"
AUDIO = ROOT / "packages/audio-symbolic-animation/SKILL.md"
WOVEN = ROOT / "packages/woven-storybook-pipeline/SKILL.md"

def run(skill, out):
    return subprocess.run([sys.executable, str(CLI), str(skill), "--output", str(out)], text=True, capture_output=True)

def load(path):
    spec = importlib.util.spec_from_file_location("generated_media_runtime", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def test_audio_compiles_deterministically_with_honest_manifest(tmp_path):
    a, b = tmp_path / "a", tmp_path / "b"
    ra, rb = run(AUDIO, a), run(AUDIO, b)
    assert ra.returncode == rb.returncode == 0, ra.stdout + ra.stderr
    for rel in ["runtime.py", "capability-manifest.json", "schemas/input.json", "schemas/output.json", "README.md", "tests/test_contract.py"]:
        assert (a / rel).read_bytes() == (b / rel).read_bytes()
    result = json.loads(ra.stdout); manifest = json.loads((a / "capability-manifest.json").read_text())
    assert result["runtime_class"] == manifest["runtime_class"] == "media-sequential"
    assert result["runtime_version"] == manifest["runtime_version"]
    assert manifest["estimated_cost_usd"] == 0
    assert manifest["cost_model"]["fixture"] == "no external provider cost"
    assert "fixture-only" in " ".join(manifest["limitations"])

def test_fixture_canary_is_sequential_checkpointed_and_complete(tmp_path):
    out = tmp_path / "generated"; assert run(AUDIO, out).returncode == 0
    runtime = load(out / "runtime.py")
    work = tmp_path / "run"
    result = asyncio.run(runtime.run_fixture(work, duration_seconds=3, checkpoint_frames=2))
    assert result["status"] == "completed"
    assert runtime.FakeFrameProvider.max_in_flight == 1
    assert [e["frame"] for e in runtime.FakeFrameProvider.events if e["event"] == "start"] == [0, 1, 2]
    assert (work / "checkpoints/checkpoint-000001.json").exists()
    for artifact in result["artifacts"]:
        assert set(artifact) == {"kind", "path", "sha256", "media_type"}
        assert (work / artifact["path"]).exists()
    assert (work / "frames/F000.ppm").exists() and (work / "frames/F002.ppm").exists()
    assert result["progress"][-1] == {"stage": "validate", "state": "completed", "completed": 3, "total": 3}
    assert abs(result["duration_seconds"] - 3) <= 0.2

def test_portrait_retry_backoff_and_resume_without_sleep(tmp_path):
    out = tmp_path / "generated"; assert run(AUDIO, out).returncode == 0
    runtime = load(out / "runtime.py")
    sleeps = []
    provider = runtime.FakeFrameProvider(landscape_once={1})
    result = asyncio.run(runtime.orchestrate({"audio_ref":"fixture://tone","duration_seconds":3}, tmp_path / "run", provider=provider, sleep=lambda seconds: sleeps.append(seconds)))
    assert result["status"] == "completed" and sleeps == [0.01]
    assert provider.attempts[1] == 2
    provider2 = runtime.FakeFrameProvider()
    resumed = asyncio.run(runtime.orchestrate({"audio_ref":"fixture://tone","duration_seconds":3}, tmp_path / "run", provider=provider2, sleep=lambda _: None))
    assert resumed["status"] == "completed" and provider2.attempts == {}

def test_missing_production_provider_is_blocked_and_creates_no_media(tmp_path):
    out = tmp_path / "generated"; assert run(AUDIO, out).returncode == 0
    runtime = load(out / "runtime.py"); work = tmp_path / "production"
    result = asyncio.run(runtime.orchestrate({"audio_ref":"upload://safe-id","duration_seconds":2}, work))
    assert result == {"status":"blocked","code":"PRODUCTION_FRAME_PROVIDER_UNAVAILABLE","retryable":False,"artifacts":[]}
    assert not work.exists()

def test_woven_is_stably_unsupported_and_creates_no_output(tmp_path):
    out = tmp_path / "woven"
    result = run(WOVEN, out); body = json.loads(result.stdout)
    assert result.returncode == 2
    assert body["status"] == "unsupported_with_reason"
    assert body["runtime_class"] == "private-document-pipeline"
    assert body["reasons"] == [
        "APPROVAL_REQUIRED_BEFORE_REAL_DATA",
        "EXTERNAL_SOURCE_REPOSITORY_UNAVAILABLE",
        "FIXTURE_ONLY_DEVELOPMENT_REQUIRED",
        "PRIVATE_DATA_ISOLATION_RETENTION_REQUIRED",
    ]
    assert not out.exists()

def test_unknown_declaration_fails_closed(tmp_path):
    text = AUDIO.read_text().replace("      checkpoint_frames: 6\n", "      checkpoint_frames: 6\n      surprise: unsafe\n")
    skill = tmp_path / "SKILL.md"; skill.write_text(text); out = tmp_path / "out"
    result = run(skill, out)
    assert result.returncode == 2 and "unsupported_runtime_declaration" in json.loads(result.stdout)["reasons"]
    assert not out.exists()
