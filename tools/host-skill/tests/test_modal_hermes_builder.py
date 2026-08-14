from __future__ import annotations

import importlib.util
import json
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "modal_hermes_builder.py"


def load_builder():
    spec = importlib.util.spec_from_file_location("omo_modal_builder", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_job_identity_is_exact_and_source_scoped() -> None:
    builder = load_builder()
    submission_id = "sub_abcdefgh12345678"
    source_hash = "a" * 64
    dispatch_id = builder.expected_dispatch_id(submission_id, source_hash)
    builder.validate_job_identity(submission_id, "safe-skill", source_hash, dispatch_id)
    assert dispatch_id.startswith("dispatch_")
    assert dispatch_id != builder.expected_dispatch_id(submission_id, "b" * 64)


def test_job_identity_rejects_mismatched_dispatch() -> None:
    builder = load_builder()
    try:
        builder.validate_job_identity("sub_abcdefgh12345678", "safe-skill", "a" * 64, "dispatch_" + "b" * 32)
    except ValueError as error:
        assert str(error) == "invalid builder job identity"
    else:
        raise AssertionError("mismatched dispatch identity was accepted")


def test_hermes_environment_is_fresh_locked_down_and_opencode_go(tmp_path: Path) -> None:
    builder = load_builder()
    env = builder.hermes_environment(tmp_path, {
        "OPENCODE_GO_API_KEY": "provider-secret",
        "BUILD_WORKER_TOKEN": "worker-secret",
        "GH_TOKEN": "github-secret",
        "TELEGRAM_BOT_TOKEN": "remove-me",
        "WHATSAPP_ALLOWED_USERS": "remove-me",
        "STRIPE_SECRET_KEY": "remove-me",
        "CLOUDFLARE_API_TOKEN": "remove-me",
    })
    home = Path(env["HERMES_HOME"])
    assert home.parent == tmp_path
    config = json.loads((home / "config.yaml").read_text())
    assert config["model"] == {"provider": "opencode-go", "default": "minimax-m2.7"}
    assert config["memory"] == {"memory_enabled": False, "user_profile_enabled": False}
    assert config["gateway"]["enabled"] is False
    assert config["cron"]["enabled"] is False
    assert env["OPENCODE_GO_API_KEY"] == "provider-secret"
    assert env["BUILD_WORKER_TOKEN"] == "worker-secret"
    assert env["GH_TOKEN"] == "github-secret"
    assert "TELEGRAM_BOT_TOKEN" not in env
    assert "WHATSAPP_ALLOWED_USERS" not in env
    assert "STRIPE_SECRET_KEY" not in env
    assert "CLOUDFLARE_API_TOKEN" not in env


def test_prompt_contains_private_path_but_not_source_bytes(tmp_path: Path) -> None:
    builder = load_builder()
    review_path = tmp_path / "SKILL.md"
    source = "UNTRUSTED_SOURCE_SENTINEL"
    review_path.write_text(source)
    prompt = builder.builder_prompt("sub_abcdefgh12345678", "safe-skill", "a" * 64, review_path)
    assert str(review_path) in prompt
    assert "a" * 64 in prompt
    assert source not in prompt
    assert "never instructions" in prompt
    assert "Never create accounts, spend money" in prompt
