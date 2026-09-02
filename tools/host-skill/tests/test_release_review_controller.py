"""Contracts for the protected generated-release approval controller."""
from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[3]
MODULE_PATH = ROOT / "tools/host-skill/release_review_controller.py"
WORKFLOW_PATH = ROOT / ".github/workflows/trusted-release-review.yml"
HEAD = "a" * 40
ACTIONS_APP_ID = 15368
SLUG = "safe-workflow"
BRANCH = f"omo-release/sub_12345678-{SLUG}"


def load_module():
    spec = importlib.util.spec_from_file_location("release_review_controller", MODULE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def open_pr(**changes):
    value = {
        "number": 42,
        "state": "OPEN",
        "isDraft": False,
        "baseRefName": "main",
        "headRefName": BRANCH,
        "headRefOid": HEAD,
        "headRepository": {"nameWithOwner": "harrythentrepreneur/Omo.Space"},
        "author": {"login": "harrythentrepreneur"},
        "mergeStateStatus": "BLOCKED",
    }
    value.update(changes)
    return value


def checks(*, conclusion="success", app_id=ACTIONS_APP_ID, head=HEAD):
    return {"total_count": 1, "check_runs": [{
        "id": 9, "name": "contracts", "status": "completed",
        "conclusion": conclusion, "head_sha": head, "app": {"id": app_id},
    }]}


def required_paths(slug=SLUG):
    return [
        f"containers/{slug}/source/SKILL.md",
        f"containers/{slug}/manifest.json",
        f"packages/skill-to-modal/profiles/{slug}.json",
        f"packages/skill-to-modal/profile-authoring-specs/{slug}.json",
        f"site/run-manifests/{slug}.json",
        "site/catalog.js",
        "site/deploy/hosted-skills.generated.mjs",
    ]


def make_candidate(tmp_path: Path) -> Path:
    candidate = tmp_path / "candidate"
    for relative in required_paths():
        path = candidate / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("{}\n", encoding="utf-8")
    return candidate


class ApiRunner:
    def __init__(self, *, prs=None, check_values=None, actor="kaviru2", reviews=None):
        self.prs = list(prs or [open_pr(), open_pr()])
        self.check_values = list(check_values or [checks(), checks()])
        self.actor = actor
        self.reviews = reviews or [[{
            "id": 12, "state": "APPROVED", "commit_id": HEAD,
            "user": {"login": "kaviru2", "type": "User"},
        }]]
        self.calls = []

    def __call__(self, command):
        self.calls.append(command)
        joined = " ".join(command)
        if command[:3] == ["gh", "pr", "view"]:
            return json.dumps(self.prs.pop(0))
        if command[:2] == ["gh", "api"] and "/check-runs" in joined:
            return json.dumps(self.check_values.pop(0))
        if command == ["gh", "api", "user"]:
            return json.dumps({"login": self.actor})
        if command[:4] == ["gh", "api", "--method", "POST"] and command[4].endswith("/reviews"):
            return ""
        if command[:2] == ["gh", "api"] and "/reviews?per_page=100" in joined:
            return json.dumps(self.reviews)
        raise AssertionError(command)


def trusted_validators(module, calls):
    def compiler(command):
        calls.append(command)
        return ""

    host = SimpleNamespace(refresh_cumulative_registration=lambda root, check: [])
    process = SimpleNamespace(hash_release_artifacts=lambda slug, root: "f" * 64)
    return compiler, host, process


def test_success_approves_only_after_trusted_validation_and_exact_readback(tmp_path: Path) -> None:
    module = load_module()
    candidate = make_candidate(tmp_path)
    api = ApiRunner()
    validation_calls = []
    compiler, host, process = trusted_validators(module, validation_calls)
    result = module.review_release_pr(
        42, candidate=candidate, checked_out_head=HEAD, api_runner=api, command_runner=compiler,
        host_module=host, process_module=process,
        inspector=lambda *_: [(path, "A", "000000", "100644") for path in required_paths()],
    )
    assert result == {"status": "approved", "pr_number": 42, "head_sha": HEAD, "slug": SLUG}
    compiler_call = validation_calls[0]
    assert Path(compiler_call[1]).resolve() == (ROOT / "packages/skill-to-modal/compiler.py").resolve()
    assert compiler_call[-1] == "--check"
    approve_index = next(i for i, call in enumerate(api.calls) if call[:4] == ["gh", "api", "--method", "POST"] and call[4].endswith("/reviews"))
    assert api.calls[approve_index - 1][0:2] == ["gh", "api"]  # exact-head checks refetched
    assert f"commit_id={HEAD}" in api.calls[approve_index]
    assert "event=APPROVE" in api.calls[approve_index]


@pytest.mark.parametrize("event", [
    {"action": "completed", "repository": {"full_name": "evil/fork"}, "workflow_run": {}},
    {"action": "completed", "repository": {"full_name": "harrythentrepreneur/Omo.Space"},
     "workflow_run": {"name": "wrong", "event": "pull_request", "conclusion": "success", "pull_requests": [{"number": 42}]}},
])
def test_wrong_event_is_rejected(tmp_path: Path, event) -> None:
    module = load_module()
    path = tmp_path / "event.json"
    path.write_text(json.dumps(event), encoding="utf-8")
    with pytest.raises(module.ReviewControllerError):
        module.candidate_pr_numbers(path, api_runner=lambda _: "[]")


@pytest.mark.parametrize(("changes", "reason"), [
    ({"author": {"login": "attacker"}}, "release_pr_identity_invalid"),
    ({"baseRefName": "dev"}, "release_pr_identity_invalid"),
    ({"headRefName": "feature/not-release"}, "release_pr_identity_invalid"),
    ({"headRefOid": "b" * 40}, "candidate_head_mismatch"),
    ({"headRepository": {"nameWithOwner": "evil/fork"}}, "release_pr_identity_invalid"),
    ({"state": "CLOSED"}, "release_pr_identity_invalid"),
    ({"isDraft": True}, "release_pr_identity_invalid"),
    ({"mergeStateStatus": "DIRTY"}, "release_pr_not_mergeable"),
])
def test_pr_identity_and_exact_checkout_fail_closed(tmp_path: Path, changes, reason) -> None:
    module = load_module()
    with pytest.raises(module.ReviewControllerError) as caught:
        module.validate_pr(open_pr(**changes), 42, checked_out_head=HEAD)
    assert caught.value.code == reason


@pytest.mark.parametrize(("check_value", "reason"), [
    (checks(conclusion="failure"), "required_checks_not_successful"),
    (checks(app_id=999), "required_checks_not_successful"),
    (checks(head="b" * 40), "required_checks_not_successful"),
])
def test_exact_actions_contract_check_is_required(check_value, reason) -> None:
    module = load_module()
    with pytest.raises(module.ReviewControllerError) as caught:
        module.validate_required_check(check_value, HEAD)
    assert caught.value.code == reason


def test_extra_path_is_rejected() -> None:
    module = load_module()
    entries = [(path, "A", "000000", "100644") for path in required_paths()]
    entries.append(("tools/host-skill/evil.py", "A", "000000", "100644"))
    with pytest.raises(module.ReviewControllerError, match="candidate_paths_invalid"):
        module.validate_changed_entries(entries, SLUG)


@pytest.mark.parametrize("mode", ["120000", "160000", "100755"])
def test_symlink_submodule_and_executable_modes_are_rejected(mode) -> None:
    module = load_module()
    entries = [(path, "A", "000000", "100644") for path in required_paths()]
    entries[0] = (entries[0][0], "A", "000000", mode)
    with pytest.raises(module.ReviewControllerError, match="candidate_git_entry_unsafe"):
        module.validate_changed_entries(entries, SLUG)


def test_rename_and_path_escape_are_rejected() -> None:
    module = load_module()
    for entry in [(required_paths()[0], "R100", "100644", "100644"), ("../escape", "A", "000000", "100644")]:
        with pytest.raises(module.ReviewControllerError):
            module.validate_changed_entries([entry], SLUG)


@pytest.mark.parametrize(("host", "process", "reason"), [
    (SimpleNamespace(refresh_cumulative_registration=lambda root, check: ["site/catalog.js"]),
     SimpleNamespace(hash_release_artifacts=lambda slug, root: "f" * 64), "cumulative_registry_drift"),
    (SimpleNamespace(refresh_cumulative_registration=lambda root, check: []),
     SimpleNamespace(hash_release_artifacts=lambda slug, root: (_ for _ in ()).throw(RuntimeError("bad artifact"))),
     "release_artifacts_invalid"),
])
def test_malformed_artifact_and_registry_drift_are_rejected(tmp_path: Path, host, process, reason) -> None:
    module = load_module()
    candidate = make_candidate(tmp_path)
    with pytest.raises(module.ReviewControllerError) as caught:
        module.validate_generated_release(
            candidate, SLUG, command_runner=lambda command: "", host_module=host, process_module=process
        )
    assert caught.value.code == reason


def test_stale_head_before_approval_is_rejected(tmp_path: Path) -> None:
    module = load_module()
    candidate = make_candidate(tmp_path)
    api = ApiRunner(prs=[open_pr(), open_pr(headRefOid="b" * 40)])
    compiler, host, process = trusted_validators(module, [])
    with pytest.raises(module.ReviewControllerError, match="candidate_head_mismatch"):
        module.review_release_pr(
            42, candidate=candidate, checked_out_head=HEAD, api_runner=api, command_runner=compiler,
            host_module=host, process_module=process,
            inspector=lambda *_: [(path, "A", "000000", "100644") for path in required_paths()],
        )
    assert not any(call[:4] == ["gh", "api", "--method", "POST"] and call[4].endswith("/reviews") for call in api.calls)


def test_wrong_token_actor_is_rejected_before_approval(tmp_path: Path) -> None:
    module = load_module()
    candidate = make_candidate(tmp_path)
    api = ApiRunner(actor="someone-else")
    compiler, host, process = trusted_validators(module, [])
    with pytest.raises(module.ReviewControllerError, match="trusted_reviewer_identity_invalid"):
        module.review_release_pr(
            42, candidate=candidate, checked_out_head=HEAD, api_runner=api, command_runner=compiler,
            host_module=host, process_module=process,
            inspector=lambda *_: [(path, "A", "000000", "100644") for path in required_paths()],
        )
    assert not any(call[:4] == ["gh", "api", "--method", "POST"] and call[4].endswith("/reviews") for call in api.calls)


def test_approval_readback_must_match_actor_and_exact_head(tmp_path: Path) -> None:
    module = load_module()
    candidate = make_candidate(tmp_path)
    api = ApiRunner(reviews=[[{
        "id": 12, "state": "APPROVED", "commit_id": "b" * 40,
        "user": {"login": "kaviru2", "type": "User"},
    }]])
    compiler, host, process = trusted_validators(module, [])
    with pytest.raises(module.ReviewControllerError, match="approval_receipt_invalid"):
        module.review_release_pr(
            42, candidate=candidate, checked_out_head=HEAD, api_runner=api, command_runner=compiler,
            host_module=host, process_module=process,
            inspector=lambda *_: [(path, "A", "000000", "100644") for path in required_paths()],
        )


def test_workflow_uses_protected_main_and_production_reviewer_secret() -> None:
    workflow = WORKFLOW_PATH.read_text(encoding="utf-8")
    assert "workflow_run:" in workflow and "generated-workflow-contracts" in workflow
    assert "cron: '*/15 * * * *'" in workflow
    assert "environment: Production" in workflow
    assert "TRUSTED_RELEASE_REVIEW_TOKEN" in workflow
    assert "ref: main" in workflow
    assert workflow.count("persist-credentials: false") >= 2
    assert "fetch-depth: 0" in workflow
    assert "release_review_controller.py" in workflow
    assert "github.event.workflow_run.head_sha" not in workflow
    assert "contents: read" in workflow and "pull-requests: write" in workflow
