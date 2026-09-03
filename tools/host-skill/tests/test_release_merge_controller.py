"""Contracts for the protected autonomous release-PR merge controller."""
from __future__ import annotations

import importlib.util
import json
import os
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
MODULE_PATH = ROOT / "tools/host-skill/release_merge_controller.py"
HEAD = "a" * 40
MERGE = "b" * 40
ACTIONS_APP_ID = 15368
SUBMISSION = "sub_" + "1" * 32


def load_module():
    spec = importlib.util.spec_from_file_location("release_merge_controller", MODULE_PATH)
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
        "headRefName": f"omo-release/{SUBMISSION}-safe-workflow",
        "headRefOid": HEAD,
        "headRepository": {"nameWithOwner": "harrythentrepreneur/Omo.Space"},
        "author": {"login": "harrythentrepreneur"},
        "reviewDecision": "APPROVED",
        "mergeStateStatus": "CLEAN",
        "mergeCommit": None,
        "labels": [],
    }
    value.update(changes)
    return value


def review(review_id=7, state="APPROVED", commit_id=HEAD, login="kaviru2"):
    return {
        "id": review_id,
        "state": state,
        "commit_id": commit_id,
        "submitted_at": "2026-08-26T00:00:00Z",
        "user": {"login": login, "type": "User"},
    }


def check_runs(conclusion="success", app_id=ACTIONS_APP_ID, run_id=7):
    return {
        "total_count": 1,
        "check_runs": [{
            "id": run_id,
            "name": "contracts",
            "status": "completed",
            "conclusion": conclusion,
            "app": {"id": app_id},
            "head_sha": HEAD,
        }],
    }


def successful_runner(
    calls, *, reviews=None, pr_changes=None, check_value=None,
    merge_value=None,
):
    current = open_pr(**(pr_changes or {}))
    views = [current, current, open_pr(state="MERGED", mergeCommit={"oid": MERGE})]
    review_pages = reviews if reviews is not None else [[review()]]

    def runner(command):
        calls.append(command)
        joined = " ".join(command)
        if command[:2] == ["gh", "api"] and joined.endswith("/protection"):
            raise AssertionError("merge path must not require Administration: read")
        if command[:3] == ["gh", "pr", "view"]:
            return json.dumps(views.pop(0))
        if command[:3] == ["gh", "pr", "list"]:
            return json.dumps([open_pr()])
        if command[:2] == ["gh", "api"] and "/reviews?per_page=100" in joined:
            return json.dumps(review_pages)
        if command[:2] == ["gh", "api"] and "/check-runs?per_page=100" in joined:
            return json.dumps(check_value or check_runs())
        if command[:4] == ["gh", "api", "--method", "PUT"] and joined.endswith("/pulls/42/merge -f sha=" + HEAD + " -f merge_method=squash"):
            return json.dumps(merge_value if merge_value is not None else {
                "sha": MERGE, "merged": True, "message": "Pull Request successfully merged",
            })
        raise AssertionError(command)

    return runner


def test_merges_only_exact_head_after_kaviru2_review_and_actions_check() -> None:
    module = load_module()
    calls = []
    result = module.merge_release_pr(42, runner=successful_runner(calls))
    assert result == {"status": "merged", "pr_number": 42, "head_sha": HEAD, "merge_sha": MERGE}
    merge = next(command for command in calls if command[:4] == ["gh", "api", "--method", "PUT"])
    assert merge == [
        "gh", "api", "--method", "PUT",
        f"repos/{module.REPOSITORY}/pulls/42/merge",
        "-f", f"sha={HEAD}", "-f", "merge_method=squash",
    ]
    assert not any("/branches/main/protection" in " ".join(command) for command in calls)
    assert not any("deploy" in " ".join(command).lower() for command in calls)


def test_exact_review_history_is_authoritative_when_review_decision_is_stale() -> None:
    module = load_module()
    calls = []
    result = module.merge_release_pr(
        42,
        runner=successful_runner(calls, pr_changes={
            "reviewDecision": "REVIEW_REQUIRED",
            "mergeStateStatus": "BLOCKED",
        }),
    )
    assert result == {"status": "merged", "pr_number": 42, "head_sha": HEAD, "merge_sha": MERGE}
    assert any("/pulls/42/merge" in " ".join(command) for command in calls)


def test_real_github_review_ids_above_signed_32_bit_are_valid() -> None:
    module = load_module()
    result = module.merge_release_pr(
        42,
        runner=successful_runner([], reviews=[[review(review_id=5_095_757_861)]]),
    )
    assert result["status"] == "merged"


def test_older_open_release_for_same_slug_is_never_merged() -> None:
    module = load_module()
    calls = []
    newer = open_pr(
        number=43,
        headRefName="omo-release/sub_" + "2" * 32 + "-safe-workflow",
        headRefOid="c" * 40,
    )
    base_runner = successful_runner(calls)

    def runner(command):
        if command[:3] == ["gh", "pr", "list"]:
            calls.append(command)
            return json.dumps([open_pr(), newer])
        return base_runner(command)

    with pytest.raises(module.MergeControllerError, match="superseded_release_pr"):
        module.merge_release_pr(42, runner=runner)
    assert not any(call[:4] == ["gh", "api", "--method", "PUT"] for call in calls)


def test_older_release_stays_superseded_after_newer_same_slug_is_closed() -> None:
    module = load_module()
    calls = []
    newer = open_pr(
        number=43,
        state="MERGED",
        headRefName="omo-release/sub_" + "2" * 32 + "-safe-workflow",
        headRefOid="c" * 40,
    )
    base_runner = successful_runner(calls)

    def runner(command):
        if command[:3] == ["gh", "pr", "list"]:
            calls.append(command)
            return json.dumps([open_pr(), newer])
        return base_runner(command)

    with pytest.raises(module.MergeControllerError, match="superseded_release_pr"):
        module.merge_release_pr(42, runner=runner)
    assert not any(call[:4] == ["gh", "api", "--method", "PUT"] for call in calls)


def test_behind_latest_release_uses_identity_separated_regeneration(monkeypatch) -> None:
    module = load_module()
    old_head = HEAD
    new_head = "c" * 40
    behind = open_pr(mergeStateStatus="BEHIND", reviewDecision="REVIEW_REQUIRED")
    views = [behind, behind]
    calls = []
    observed = {}

    def runner(command):
        calls.append(command)
        if command[:3] == ["gh", "pr", "view"]:
            return json.dumps(views.pop(0))
        if command[:3] == ["gh", "pr", "list"]:
            return json.dumps([behind])
        raise AssertionError(command)

    def reconcile(number, pr, head, gh_runner, repo_root):
        observed.update(number=number, pr=pr, head=head, repo_root=repo_root)
        return new_head

    monkeypatch.setattr(module, "_regenerate_dirty_release", reconcile)
    assert module.merge_release_pr(42, runner=runner, repo_root=Path("/trusted/controller")) == {
        "status": "regenerated",
        "pr_number": 42,
        "previous_head_sha": old_head,
        "head_sha": new_head,
    }
    assert observed == {
        "number": 42, "pr": behind, "head": old_head,
        "repo_root": Path("/trusted/controller"),
    }
    assert not any("/update-branch" in " ".join(call) for call in calls)
    assert not any("/pulls/42/merge" in " ".join(call) for call in calls)


@pytest.mark.parametrize(
    "receipt",
    [
        [],
        {"sha": MERGE, "merged": False, "message": "blocked"},
        {"sha": "bad", "merged": True, "message": "merged"},
        {"sha": MERGE, "merged": True, "message": ""},
    ],
)
def test_rest_merge_receipt_must_confirm_a_valid_merge(receipt) -> None:
    module = load_module()
    calls = []
    runner = successful_runner(calls, merge_value=receipt)
    with pytest.raises(module.MergeControllerError, match="merge_receipt_invalid"):
        module.merge_release_pr(42, runner=runner)
    assert len([call for call in calls if call[:4] == ["gh", "api", "--method", "PUT"]]) == 1


def test_mutable_pr_identity_is_revalidated_immediately_before_merge() -> None:
    module = load_module()
    calls = []
    views = [open_pr(), open_pr(baseRefName="other")]
    base_runner = successful_runner(calls)

    def runner(command):
        if command[:3] == ["gh", "pr", "view"]:
            calls.append(command)
            return json.dumps(views.pop(0))
        return base_runner(command)

    with pytest.raises(module.MergeControllerError, match="release_pr_identity_invalid"):
        module.merge_release_pr(42, runner=runner)
    assert not any("/pulls/42/merge" in " ".join(call) for call in calls)


def test_latest_matching_contracts_check_must_be_successful_and_well_typed() -> None:
    module = load_module()
    older = check_runs(run_id=7)["check_runs"][0]
    newer = check_runs(conclusion="failure", run_id=8)["check_runs"][0]
    with pytest.raises(module.MergeControllerError, match="required_checks_not_successful"):
        module.merge_release_pr(
            42,
            runner=successful_runner(
                [], check_value={"total_count": 2, "check_runs": [older, newer]}
            ),
        )

    malformed = dict(newer)
    malformed["id"] = "bad"
    with pytest.raises(module.MergeControllerError, match="github_response_invalid"):
        module.merge_release_pr(
            42,
            runner=successful_runner(
                [], check_value={"total_count": 2, "check_runs": [older, malformed]}
            ),
        )

    float_app = check_runs()["check_runs"][0]
    float_app["app"] = {"id": float(ACTIONS_APP_ID)}
    with pytest.raises(module.MergeControllerError, match="github_response_invalid"):
        module.merge_release_pr(
            42,
            runner=successful_runner(
                [], check_value={"total_count": 1, "check_runs": [float_app]}
            ),
        )

    assert module.merge_release_pr(
        42,
        runner=successful_runner([], check_value=check_runs(run_id=3_000_000_000)),
    )["status"] == "merged"


@pytest.mark.parametrize(
    ("reviews", "pr_changes", "check_value", "blocker"),
    [
        ([[review(login="someone-else")]], None, None, "separate_review_required"),
        ([[review(commit_id="c" * 40)]], None, None, "exact_head_review_required"),
        ([[review(), review(8, state="DISMISSED")]], None, None, "separate_review_required"),
        ([[review(), review(8, state="CHANGES_REQUESTED")]], None, None, "separate_review_required"),
        (None, {"headRepository": {"nameWithOwner": "evil/fork"}}, None, "release_pr_identity_invalid"),
        (None, {"author": {"login": "kaviru2"}}, None, "release_pr_identity_invalid"),
        (None, None, check_runs(app_id=999), "required_checks_not_successful"),
        (None, None, check_runs(conclusion="failure"), "required_checks_not_successful"),
    ],
)
def test_controller_fails_closed_without_merge(reviews, pr_changes, check_value, blocker) -> None:
    module = load_module()
    calls = []
    runner = successful_runner(
        calls,
        reviews=reviews,
        pr_changes=pr_changes,
        check_value=check_value,
    )
    with pytest.raises(module.MergeControllerError) as caught:
        module.merge_release_pr(42, runner=runner)
    assert caught.value.code == blocker
    assert not any(command[:4] == ["gh", "api", "--method", "PUT"] for command in calls)


def test_review_pagination_accepts_exact_review_after_first_30() -> None:
    module = load_module()
    calls = []
    page_one = [review(i + 1, login=f"reviewer-{i}") for i in range(30)]
    page_two = [review(100, login="kaviru2")]
    assert module.merge_release_pr(
        42, runner=successful_runner(calls, reviews=[page_one, page_two])
    )["status"] == "merged"
    review_call = next(command for command in calls if "/reviews?per_page=100" in " ".join(command))
    assert "--paginate" in review_call and "--slurp" in review_call


@pytest.mark.parametrize(
    ("workflow_name", "workflow_event"),
    [
        ("generated-workflow-contracts", "push"),
        ("trusted-release-review", "workflow_run"),
    ],
)
def test_trusted_default_branch_completions_reconcile_open_release_prs(
    tmp_path: Path, workflow_name: str, workflow_event: str,
) -> None:
    module = load_module()
    event = tmp_path / "workflow-run.json"
    event.write_text(json.dumps({
        "action": "completed",
        "repository": {"full_name": module.REPOSITORY},
        "workflow_run": {
            "name": workflow_name,
            "event": workflow_event,
            "conclusion": "success",
            "pull_requests": [],
        },
    }))

    def runner(command):
        assert command[:3] == ["gh", "pr", "list"]
        assert command[command.index("--limit") + 1] == str(module.MAX_CANDIDATES + 1)
        return json.dumps([
            {"number": 42, "headRefName": f"omo-release/{SUBMISSION}-safe-workflow"},
            {"number": 9, "headRefName": "ordinary-feature"},
        ])

    assert module.candidate_pr_numbers(event, runner=runner) == [42]


def test_candidate_scan_detects_truncation_instead_of_starving_release_prs(tmp_path: Path) -> None:
    module = load_module()
    event = tmp_path / "schedule.json"
    event.write_text(json.dumps({
        "schedule": "*/5 * * * *",
        "repository": {"full_name": module.REPOSITORY},
    }))
    rows = [{"number": index + 1, "headRefName": f"ordinary-{index}"}
            for index in range(module.MAX_CANDIDATES + 1)]

    with pytest.raises(module.MergeControllerError, match="github_response_invalid"):
        module.candidate_pr_numbers(event, runner=lambda _command: json.dumps(rows))


def test_scheduled_candidates_are_isolated_when_one_is_malformed(tmp_path: Path) -> None:
    module = load_module()
    event = tmp_path / "schedule.json"
    event.write_text(json.dumps({
        "schedule": "*/5 * * * *",
        "repository": {"full_name": module.REPOSITORY},
    }))
    valid_views = [
        open_pr(number=42),
        open_pr(number=42),
        open_pr(number=42, state="MERGED", mergeCommit={"oid": MERGE}),
    ]

    def runner(command):
        joined = " ".join(command)
        if command[:3] == ["gh", "pr", "list"]:
            if "number,state,isDraft" in joined:
                return json.dumps([open_pr(number=42)])
            return json.dumps([
                {"number": 41, "headRefName": "omo-release/sub_" + "1" * 32 + "-one"},
                {"number": 42, "headRefName": "omo-release/sub_" + "2" * 32 + "-two"},
            ])
        if command[:4] == ["gh", "pr", "view", "41"]:
            return json.dumps(open_pr(number=41))
        if command[:4] == ["gh", "pr", "view", "42"]:
            return json.dumps(valid_views.pop(0))
        if command[:2] == ["gh", "api"] and "/pulls/41/reviews?per_page=100" in joined:
            malformed = review(review_id=8)
            malformed["id"] = "malformed"
            return json.dumps([[review(), malformed]])
        if command[:2] == ["gh", "api"] and "/pulls/42/reviews?per_page=100" in joined:
            return json.dumps([[review()]])
        if command[:2] == ["gh", "api"] and "/check-runs?per_page=100" in joined:
            return json.dumps(check_runs())
        if command[:4] == ["gh", "api", "--method", "PUT"] and "/pulls/42/merge" in joined:
            return json.dumps({"sha": MERGE, "merged": True, "message": "Pull Request successfully merged"})
        raise AssertionError(command)

    result = module.run(event, runner=runner)
    assert result["results"] == [
        {"status": "blocked", "pr_number": 41, "reason": "github_response_invalid"},
        {"status": "merged", "pr_number": 42, "head_sha": HEAD, "merge_sha": MERGE},
    ]


def test_cli_fails_the_workflow_when_any_candidate_is_blocked(tmp_path: Path, monkeypatch, capsys) -> None:
    module = load_module()
    event = tmp_path / "event.json"
    event.write_text("{}")
    monkeypatch.setattr(module, "run", lambda _path: {
        "status": "complete",
        "results": [{"status": "blocked", "pr_number": 42, "reason": "github_command_failed"}],
    })
    assert module.main(["--event", str(event)]) == 1
    assert '"status":"blocked"' in capsys.readouterr().out

    monkeypatch.setattr(module, "run", lambda _path: {
        "status": "complete",
        "results": [{"status": "waiting", "pr_number": 42, "reason": "separate_review_required"}],
    })
    assert module.main(["--event", str(event)]) == 0


def test_merge_workflow_loads_controller_only_from_main() -> None:
    workflow = (ROOT / ".github/workflows/trusted-release-merge.yml").read_text()
    assert "pull_request_review:" not in workflow
    assert "workflow_run:" in workflow
    assert "workflows: [generated-workflow-contracts, trusted-release-review]" in workflow
    assert "cron: '*/5 * * * *'" in workflow
    assert "contents: write" in workflow and "pull-requests: write" in workflow
    assert "environment: Production" in workflow
    assert "GH_TOKEN: ${{ secrets.TRUSTED_RELEASE_REVIEW_TOKEN }}" in workflow
    assert "GH_TOKEN: ${{ github.token }}" not in workflow
    assert "ref: main" in workflow and "fetch-depth: 0" in workflow
    assert "token: ${{ github.token }}" in workflow
    assert "token: ${{ secrets.TRUSTED_RELEASE_REVIEW_TOKEN }}" not in workflow
    assert "persist-credentials: true" in workflow
    assert "path: controller" in workflow
    assert "if [ ! -f controller/tools/host-skill/release_merge_controller.py ]; then" in workflow
    assert "exit 0" in workflow
    assert "python3 controller/tools/host-skill/release_merge_controller.py" in workflow
    assert "github.event.pull_request.head.sha" not in workflow

    contracts = (ROOT / ".github/workflows/generated-workflow-contracts.yml").read_text()
    assert "types: [opened, synchronize, reopened, labeled]" in contracts
    assert "github.event.action != 'labeled' || github.event.label.name == 'omo-release-recheck'" in contracts


def git(repo: Path, *args: str, env: dict[str, str] | None = None) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        text=True,
        env={**os.environ, **(env or {})},
    )
    return result.stdout.strip()


def commit_all(repo: Path, message: str) -> str:
    git(repo, "add", "--all")
    git(
        repo,
        "-c", "user.name=Release Test",
        "-c", "user.email=release@example.invalid",
        "commit", "-m", message,
    )
    return git(repo, "rev-parse", "HEAD")


def write_release(repo: Path, slug: str, marker: str, sentinel: Path | None = None) -> None:
    container = repo / "containers" / slug
    container.mkdir(parents=True, exist_ok=True)
    (container / "manifest.json").write_text(json.dumps({"slug": slug, "marker": marker}))
    (container / "hosted-profile.json").write_text(json.dumps({"slug": slug}))
    if sentinel is not None:
        (container / "candidate.py").write_text(
            "from pathlib import Path\nPath(" + repr(str(sentinel)) + ").write_text('executed')\n"
        )
    profile = repo / "packages" / "skill-to-modal" / "profiles" / f"{slug}.json"
    receipt = repo / "packages" / "skill-to-modal" / "profile-authoring-specs" / f"{slug}.json"
    run_manifest = repo / "site" / "run-manifests" / f"{slug}.json"
    for path, value in (
        (profile, {"slug": slug, "marker": marker}),
        (receipt, {"slug": slug, "receipt": marker}),
        (run_manifest, {"slug": slug, "run": marker}),
    ):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value))


def install_trusted_test_host(repo: Path) -> None:
    host = repo / "tools" / "host-skill" / "host.py"
    host.parent.mkdir(parents=True, exist_ok=True)
    host.write_text(
        "import json\n"
        "from pathlib import Path\n"
        "def refresh_cumulative_registration(root: Path, check: bool = False):\n"
        "    profiles = sorted(json.loads(p.read_text())['slug'] for p in "
        "(root / 'packages/skill-to-modal/profiles').glob('*.json'))\n"
        "    (root / 'site/catalog.js').write_text('catalog=' + json.dumps(profiles) + '\\n')\n"
        "    (root / 'site/deploy/hosted-skills.generated.mjs').write_text("
        "'registry=' + json.dumps(profiles) + '\\n')\n"
        "    return []\n"
    )


def test_dirty_release_revalidates_exact_head_and_slug_before_regeneration(monkeypatch) -> None:
    module = load_module()
    calls = []
    dirty = open_pr(mergeStateStatus="DIRTY", reviewDecision="REVIEW_REQUIRED")
    views = [dirty, dirty]
    regenerated = "d" * 40

    def runner(command):
        calls.append(command)
        if command[:3] == ["gh", "pr", "view"]:
            return json.dumps(views.pop(0))
        if command[:3] == ["gh", "pr", "list"]:
            return json.dumps([dirty])
        raise AssertionError(command)

    observed = {}

    def reconcile(number, pr, old_head, gh_runner, repo_root):
        observed.update(number=number, pr=pr, old_head=old_head, repo_root=repo_root)
        return regenerated

    monkeypatch.setattr(module, "_regenerate_dirty_release", reconcile)
    result = module.merge_release_pr(42, runner=runner, repo_root=Path("/trusted/controller"))
    assert result == {
        "status": "regenerated",
        "pr_number": 42,
        "previous_head_sha": HEAD,
        "head_sha": regenerated,
    }
    assert observed == {
        "number": 42,
        "pr": dirty,
        "old_head": HEAD,
        "repo_root": Path("/trusted/controller"),
    }
    assert len([call for call in calls if call[:3] == ["gh", "pr", "view"]]) == 2
    assert len([call for call in calls if call[:3] == ["gh", "pr", "list"]]) == 2


def test_transient_unknown_merge_state_settles_to_dirty_and_regenerates(monkeypatch) -> None:
    module = load_module()
    unknown = open_pr(mergeStateStatus="UNKNOWN", reviewDecision="REVIEW_REQUIRED")
    dirty = open_pr(mergeStateStatus="DIRTY", reviewDecision="REVIEW_REQUIRED")
    views = [unknown, dirty, dirty]

    def runner(command):
        if command[:3] == ["gh", "pr", "view"]:
            return json.dumps(views.pop(0))
        if command[:3] == ["gh", "pr", "list"]:
            return json.dumps([dirty])
        raise AssertionError(command)

    monkeypatch.setattr(module.time, "sleep", lambda _seconds: None)
    monkeypatch.setattr(module, "_regenerate_dirty_release", lambda *_args: "d" * 40)
    result = module.merge_release_pr(42, runner=runner, repo_root=Path("/trusted/controller"))
    assert result == {
        "status": "regenerated", "pr_number": 42,
        "previous_head_sha": HEAD, "head_sha": "d" * 40,
    }
    assert views == []


@pytest.mark.parametrize("unsafe_kind", ["executable", "symlink", "foreign", "deletion"])
def test_dirty_candidate_integrity_rejects_unsafe_git_delta(tmp_path: Path, unsafe_kind: str) -> None:
    module = load_module()
    repo = tmp_path / "repo"
    git(tmp_path, "init", "--initial-branch=main", str(repo))
    write_release(repo, "safe-workflow", "base")
    install_trusted_test_host(repo)
    (repo / "site" / "deploy").mkdir(parents=True, exist_ok=True)
    (repo / "site" / "catalog.js").write_text("catalog=[]\n")
    (repo / "site" / "deploy" / "hosted-skills.generated.mjs").write_text("registry=[]\n")
    base = commit_all(repo, "base")
    target = repo / "containers" / "safe-workflow" / "manifest.json"
    if unsafe_kind == "executable":
        target.chmod(0o755)
    elif unsafe_kind == "symlink":
        target.unlink()
        target.symlink_to("../../outside")
    elif unsafe_kind == "foreign":
        (repo / "foreign.txt").write_text("not slug owned")
    else:
        target.unlink()
    head = commit_all(repo, unsafe_kind)

    with pytest.raises(module.MergeControllerError, match="release_candidate_integrity_invalid"):
        module._candidate_blob_manifest(repo, base, head, "safe-workflow")


def test_real_git_dirty_regeneration_preserves_candidate_data_and_both_parents(
    tmp_path: Path, monkeypatch,
) -> None:
    module = load_module()
    origin = tmp_path / "origin.git"
    seed = tmp_path / "seed"
    git(tmp_path, "init", "--bare", str(origin))
    git(tmp_path, "clone", str(origin), str(seed))
    git(seed, "checkout", "-b", "main")
    install_trusted_test_host(seed)
    write_release(seed, "seed", "seed")
    (seed / "site" / "deploy").mkdir(parents=True, exist_ok=True)
    (seed / "site" / "catalog.js").write_text('catalog=["seed"]\n')
    (seed / "site" / "deploy" / "hosted-skills.generated.mjs").write_text('registry=["seed"]\n')
    base = commit_all(seed, "base")
    git(seed, "push", "-u", "origin", "main")

    branch_a = "omo-release/sub_" + "2" * 32 + "-release-a"
    branch_b = "omo-release/sub_" + "3" * 32 + "-release-b"
    git(seed, "checkout", "-b", branch_a, base)
    write_release(seed, "release-a", "immutable-a")
    (seed / "site" / "catalog.js").write_text('catalog=["release-a","seed"]\n')
    (seed / "site" / "deploy" / "hosted-skills.generated.mjs").write_text('registry=["release-a","seed"]\n')
    commit_all(seed, "release A")
    git(seed, "push", "origin", branch_a)

    sentinel = tmp_path / "candidate-executed"
    git(seed, "checkout", "-b", branch_b, base)
    write_release(seed, "release-b", "immutable-b", sentinel)
    (seed / "site" / "catalog.js").write_text('catalog=["release-b","seed"]\n')
    (seed / "site" / "deploy" / "hosted-skills.generated.mjs").write_text('registry=["release-b","seed"]\n')
    old_b = commit_all(seed, "release B")
    git(seed, "push", "origin", branch_b)

    git(seed, "checkout", "main")
    git(seed, "merge", "--no-ff", branch_a, "-m", "merge A")
    latest_main = git(seed, "rev-parse", "HEAD")
    git(seed, "push", "origin", "main")
    immutable_paths = [
        "containers/release-b/manifest.json",
        "containers/release-b/candidate.py",
        "packages/skill-to-modal/profiles/release-b.json",
        "packages/skill-to-modal/profile-authoring-specs/release-b.json",
        "site/run-manifests/release-b.json",
    ]
    old_blobs = {path: git(seed, "rev-parse", f"{old_b}:{path}") for path in immutable_paths}

    dirty = open_pr(
        headRefName=branch_b,
        headRefOid=old_b,
        mergeStateStatus="DIRTY",
        reviewDecision="REVIEW_REQUIRED",
    )
    pushed_head = None
    recheck_label_applied = False

    def runner(command):
        nonlocal pushed_head, recheck_label_applied
        if command[:3] == ["gh", "pr", "list"]:
            return json.dumps([dirty])
        if command[:4] == ["gh", "api", "--method", "POST"] and "/issues/42/labels" in " ".join(command):
            recheck_label_applied = True
            return json.dumps([{"name": module.CONTRACT_RECHECK_LABEL}])
        if command[:3] == ["gh", "pr", "view"]:
            remote_head = git(seed, "ls-remote", origin.as_posix(), f"refs/heads/{branch_b}").split()[0]
            if remote_head != old_b:
                pushed_head = remote_head
                return json.dumps(open_pr(
                    headRefName=branch_b,
                    headRefOid=remote_head,
                    mergeStateStatus="BLOCKED",
                    reviewDecision="REVIEW_REQUIRED",
                    labels=[{"name": module.CONTRACT_RECHECK_LABEL}] if recheck_label_applied else [],
                ))
            return json.dumps(dirty)
        raise AssertionError(command)

    git_calls = []
    real_git = module._git

    def traced_git(repo, *args, **kwargs):
        git_calls.append(args)
        return real_git(repo, *args, **kwargs)

    monkeypatch.setattr(module, "_git", traced_git)
    result = module.merge_release_pr(42, runner=runner, repo_root=seed)
    assert result["status"] == "regenerated"
    assert result["previous_head_sha"] == old_b
    assert result["head_sha"] == pushed_head
    assert pushed_head is not None
    seal_parents = git(seed, "show", "-s", "--format=%P", pushed_head).split()
    assert len(seal_parents) == 1
    reconciliation_head = seal_parents[0]
    assert git(seed, "show", "-s", "--format=%P", reconciliation_head).split() == [latest_main, old_b]
    assert git(seed, "rev-parse", f"{pushed_head}^{{tree}}") == git(seed, "rev-parse", f"{reconciliation_head}^{{tree}}")
    assert git(seed, "merge-base", "--is-ancestor", latest_main, pushed_head) == ""
    assert git(seed, "merge-base", "--is-ancestor", old_b, pushed_head) == ""
    for path, blob in old_blobs.items():
        assert git(seed, "rev-parse", f"{pushed_head}:{path}") == blob
    assert "release-a" in git(seed, "show", f"{pushed_head}:site/catalog.js")
    assert "release-b" in git(seed, "show", f"{pushed_head}:site/catalog.js")
    changed = set(git(seed, "diff", "--name-only", latest_main, pushed_head).splitlines())
    assert changed == set(immutable_paths) | {
        "containers/release-b/hosted-profile.json",
        "site/catalog.js",
        "site/deploy/hosted-skills.generated.mjs",
    }
    assert not sentinel.exists()
    push = next(args for args in git_calls if args and args[0] == "push")
    assert push == (
        "push", "origin", f"{pushed_head}:refs/heads/{branch_b}",
        f"--force-with-lease=refs/heads/{branch_b}:{old_b}",
    )
    assert "--force" not in push


def test_failed_dirty_push_distinguishes_cas_race_from_write_failure(monkeypatch) -> None:
    module = load_module()
    branch = f"omo-release/{SUBMISSION}-safe-workflow"

    def fail_push(_repo, *args, **kwargs):
        assert args[0] == "push"
        assert f"--force-with-lease=refs/heads/{branch}:{HEAD}" in args
        raise module.MergeControllerError(kwargs["error"])

    monkeypatch.setattr(module, "_git", fail_push)
    monkeypatch.setattr(
        module, "_remote_head",
        lambda _repo, ref: "c" * 40 if ref.endswith(branch) else MERGE,
    )
    with pytest.raises(module.MergeControllerError, match="release_branch_moved"):
        module._push_dirty_head(
            Path("/trusted"), branch=branch, old_head=HEAD,
            new_head="d" * 40, main_sha=MERGE,
        )

    monkeypatch.setattr(
        module, "_remote_head",
        lambda _repo, ref: HEAD if ref.endswith(branch) else MERGE,
    )
    with pytest.raises(module.MergeControllerError, match="release_push_failed"):
        module._push_dirty_head(
            Path("/trusted"), branch=branch, old_head=HEAD,
            new_head="d" * 40, main_sha=MERGE,
        )


def test_regenerated_head_triggers_fresh_contracts_without_reviewer_push_identity() -> None:
    module = load_module()
    calls = []
    current = open_pr(headRefOid="d" * 40, reviewDecision="REVIEW_REQUIRED", labels=[])

    applied = False

    def runner(command):
        nonlocal applied
        calls.append(command)
        joined = " ".join(command)
        if command[:4] == ["gh", "api", "--method", "POST"] and "/issues/42/labels" in joined:
            applied = True
            return json.dumps([{"name": module.CONTRACT_RECHECK_LABEL}])
        if command[:3] == ["gh", "pr", "view"]:
            return json.dumps({
                **current,
                "labels": [{"name": module.CONTRACT_RECHECK_LABEL}] if applied else [],
            })
        raise AssertionError(command)

    module._trigger_contracts_recheck(42, current, "d" * 40, runner)
    assert any(
        command[:4] == ["gh", "api", "--method", "POST"]
        and f"labels[]={module.CONTRACT_RECHECK_LABEL}" in command
        for command in calls
    )
    assert not any(command[:4] == ["gh", "api", "--method", "DELETE"] for command in calls)
