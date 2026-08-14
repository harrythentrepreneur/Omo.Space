#!/usr/bin/env python3
"""Compile, test, price, and register one reviewed SKILL.md for Omo hosting.

SKILL.md is always parsed as untrusted text. The adjacent reviewed JSON profile
owns schemas, capabilities, provider settings, pricing, and marketplace copy.
No command in the Markdown is executed and no credential value is read.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
COMPILER_PATH = ROOT / "packages" / "skill-to-modal" / "compiler.py"
PROFILE_ROOT = ROOT / "packages" / "skill-to-modal" / "profiles"
CONTAINER_ROOT = ROOT / "containers"
CATALOG_PATH = ROOT / "site" / "catalog.js"
RUN_MANIFEST_ROOT = ROOT / "site" / "run-manifests"
HOSTED_REGISTRY_PATH = ROOT / "site" / "deploy" / "hosted-skills.generated.mjs"
CATALOG_START = "  // host-skill:generated:start"
CATALOG_END = "  // host-skill:generated:end"
ENV_NAME_RE = re.compile(r"^[A-Z][A-Z0-9_]{1,79}$")
SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
RUNTIME_PREFERENCES = {"auto", "worker-native", "modal-hosted"}
WORKER_EXECUTOR_SPEC_VERSION = "omo.worker-single-llm/v1"
WORKER_EXECUTION_KIND = "single_llm"
WORKER_OPERATION = "chat.completions.strict_json"
WORKER_PROVIDERS = {"opencode-go"}
WORKER_MAX_OUTPUT_TOKENS_MIN = 1
WORKER_MAX_OUTPUT_TOKENS_MAX = 8000
WORKER_TEMPERATURE_MIN = 0
WORKER_TEMPERATURE_MAX = 1
WORKER_TIMEOUT_SECONDS_MIN = 1
WORKER_TIMEOUT_SECONDS_MAX = 120
WORKER_SAFE_CAPABILITIES = {
    "opencode-go-chat-completions",
    "schema-validated-json-output",
}
WORKER_SCHEMA_KEYWORDS = {
    "$id",
    "$schema",
    "additionalProperties",
    "const",
    "default",
    "description",
    "enum",
    "examples",
    "items",
    "maxItems",
    "maxLength",
    "maximum",
    "minItems",
    "minLength",
    "minimum",
    "pattern",
    "properties",
    "required",
    "title",
    "type",
}


def load_compiler() -> Any:
    spec = importlib.util.spec_from_file_location("omo_skill_to_modal_compiler", COMPILER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("could not load the reviewed skill compiler")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


COMPILER = load_compiler()


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: expected a JSON object")
    return value


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def display_path(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def js_json(value: Any, indent: int = 0) -> str:
    rendered = json.dumps(value, ensure_ascii=True, indent=2, sort_keys=True)
    prefix = " " * indent
    return "\n".join(prefix + line if line else line for line in rendered.splitlines())


def run_checked(command: list[str]) -> None:
    subprocess.run(command, cwd=ROOT, check=True)


def require_text(value: Any, field: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise ValueError(f"marketplace.{field} is required")
    return text


def validate_https_modal_endpoint(value: Any, expected_workspace: str | None = None) -> str:
    from urllib.parse import urlsplit

    endpoint = require_text(value, "deployment.default_endpoint").rstrip("/")
    parsed = urlsplit(endpoint)
    hostname = parsed.hostname or ""
    if (
        parsed.scheme != "https"
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
        or parsed.path not in {"", "/"}
        or not hostname.endswith(".modal.run")
    ):
        raise ValueError("marketplace deployment endpoint must be a bare HTTPS *.modal.run URL")
    if expected_workspace:
        prefix = f"{expected_workspace}--"
        if not hostname.startswith(prefix):
            raise ValueError("marketplace deployment endpoint workspace does not match the reviewed target")
    return endpoint


def require_bounded_int(value: Any, field: str, minimum: int, maximum: int) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < minimum or value > maximum:
        raise ValueError(f"{field} must be an integer from {minimum} to {maximum}")
    return value


def require_bounded_number(value: Any, field: str, minimum: float, maximum: float) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError(f"{field} must be a number from {minimum} to {maximum}")
    number = float(value)
    if number < minimum or number > maximum:
        raise ValueError(f"{field} must be a number from {minimum} to {maximum}")
    return number


def unsupported_schema_keywords(schema: Any, path: str = "$") -> list[str]:
    if not isinstance(schema, dict):
        return []
    unsupported = [f"{path}.{key}" for key in schema if key not in WORKER_SCHEMA_KEYWORDS]
    properties = schema.get("properties")
    if isinstance(properties, dict):
        for key, child in properties.items():
            unsupported.extend(unsupported_schema_keywords(child, f"{path}.properties.{key}"))
    items = schema.get("items")
    if isinstance(items, dict):
        unsupported.extend(unsupported_schema_keywords(items, f"{path}.items"))
    return unsupported


def worker_executor_errors(profile: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if profile.get("execution_kind") != WORKER_EXECUTION_KIND:
        errors.append("execution_kind")
    capabilities = set(profile.get("capabilities") or [])
    unsupported_capabilities = sorted(capabilities - WORKER_SAFE_CAPABILITIES)
    if unsupported_capabilities:
        errors.append("capabilities:" + ",".join(unsupported_capabilities))
    if profile.get("apt_packages"):
        errors.append("apt_packages")
    if profile.get("artifacts"):
        errors.append("artifacts")

    steps = profile.get("steps")
    if not isinstance(steps, list):
        errors.append("steps")
        steps = []
    ready_llm_steps = [
        step for step in steps
        if isinstance(step, dict) and step.get("type") == "llm" and step.get("readiness") == "ready"
    ]
    if len(ready_llm_steps) != 1 or len(steps) != 1:
        errors.append("reviewed_steps")
    step = ready_llm_steps[0] if len(ready_llm_steps) == 1 else {}
    if step.get("provider") not in WORKER_PROVIDERS:
        errors.append("provider")
    if step.get("operation") != WORKER_OPERATION:
        errors.append("operation")

    live = profile.get("live")
    if not isinstance(live, dict):
        errors.append("live")
        live = {}
    if live.get("provider") not in WORKER_PROVIDERS or (step and live.get("provider") != step.get("provider")):
        errors.append("live.provider")
    if not str(live.get("default_model") or "").strip():
        errors.append("live.default_model")
    prompt_name = live.get("prompt")
    prompts = profile.get("prompts")
    system_prompt = prompts.get(prompt_name) if isinstance(prompts, dict) else ""
    if not isinstance(prompt_name, str) or not isinstance(system_prompt, str) or not system_prompt.strip():
        errors.append("system_prompt")
    if not str(profile.get("version") or "").strip():
        errors.append("workflow_version")
    try:
        require_bounded_int(live.get("max_tokens"), "live.max_tokens", WORKER_MAX_OUTPUT_TOKENS_MIN, WORKER_MAX_OUTPUT_TOKENS_MAX)
    except ValueError:
        errors.append("max_output_tokens")
    try:
        require_bounded_number(live.get("temperature"), "live.temperature", WORKER_TEMPERATURE_MIN, WORKER_TEMPERATURE_MAX)
    except ValueError:
        errors.append("temperature")
    try:
        require_bounded_int(live.get("timeout_seconds"), "live.timeout_seconds", WORKER_TIMEOUT_SECONDS_MIN, WORKER_TIMEOUT_SECONDS_MAX)
    except ValueError:
        errors.append("timeout_seconds")
    schema_errors = unsupported_schema_keywords(profile.get("input_schema")) + unsupported_schema_keywords(profile.get("output_schema"))
    if schema_errors:
        errors.append("schema_keywords:" + ",".join(schema_errors[:8]))
    return errors


def build_worker_executor(profile: dict[str, Any]) -> dict[str, Any]:
    errors = worker_executor_errors(profile)
    if errors:
        raise ValueError("workflow is not Worker-native compatible: " + "; ".join(errors))
    live = profile["live"]
    prompt_name = live["prompt"]
    return {
        "spec_version": WORKER_EXECUTOR_SPEC_VERSION,
        "execution_kind": WORKER_EXECUTION_KIND,
        "operation": WORKER_OPERATION,
        "provider": live["provider"],
        "model": require_text(live.get("default_model"), "live.default_model"),
        "system_prompt": require_text(profile["prompts"][prompt_name], f"prompts.{prompt_name}"),
        "workflow_version": require_text(profile.get("version"), "version"),
        "max_output_tokens": require_bounded_int(
            live.get("max_tokens"), "live.max_tokens", WORKER_MAX_OUTPUT_TOKENS_MIN, WORKER_MAX_OUTPUT_TOKENS_MAX
        ),
        "temperature": require_bounded_number(
            live.get("temperature"), "live.temperature", WORKER_TEMPERATURE_MIN, WORKER_TEMPERATURE_MAX
        ),
        "timeout_seconds": require_bounded_int(
            live.get("timeout_seconds"), "live.timeout_seconds", WORKER_TIMEOUT_SECONDS_MIN, WORKER_TIMEOUT_SECONDS_MAX
        ),
    }


def decide_runtime_placement(profile: dict[str, Any]) -> dict[str, Any]:
    preference_declared = "runtime_preference" in profile
    requested = str(profile.get("runtime_preference", "modal-hosted")).strip()
    if requested not in RUNTIME_PREFERENCES:
        raise ValueError("runtime_preference must be auto, worker-native, or modal-hosted")
    worker_errors = worker_executor_errors(profile)
    worker_compatible = not worker_errors
    if worker_compatible:
        recommended = "worker-native"
        effective = recommended if requested == "auto" else requested
        reason = (
            "creator_selected_modal" if effective == "modal-hosted"
            else "bounded_single_llm_is_worker_compatible"
        )
    else:
        recommended = "modal-hosted"
        if requested == "worker-native":
            detail = "; ".join(worker_errors)
            raise ValueError(f"workflow requires Modal; Worker override is incompatible: {detail}")
        effective = "modal-hosted"
        reason = "worker_executor_contract_not_satisfied"
    if not preference_declared:
        effective = "modal-hosted"
        requested = "modal-hosted"
        reason = "legacy_profile_defaults_to_modal"
    return {
        "recommended": recommended,
        "requested": requested,
        "effective": effective,
        "compatible": True,
        "reason": reason,
    }


def build_hosted_profile(
    profile: dict[str, Any], container_manifest: dict[str, Any], pricing: dict[str, Any]
) -> dict[str, Any]:
    market = profile.get("marketplace")
    if not isinstance(market, dict):
        raise ValueError("the reviewed profile needs a marketplace object before registration")
    slug = require_text(market.get("slug"), "slug")
    if not SLUG_RE.fullmatch(slug):
        raise ValueError("marketplace.slug must be lowercase kebab-case")
    if not container_manifest.get("readiness", {}).get("can_submit"):
        raise ValueError("blocked containers cannot be registered as runnable")
    if not container_manifest.get("pricing", {}).get("chargeable"):
        raise ValueError("hosted marketplace profiles must have reviewed chargeable pricing")
    price_usd = float(pricing["display_price_usd"])
    run_price_cents = round(price_usd * 100)
    if run_price_cents < 1 or abs(price_usd - run_price_cents / 100) > 0.000001:
        raise ValueError("display price must resolve to whole USD cents")
    reviewed_source_sha256 = require_text(container_manifest.get("source_sha256"), "source_sha256")
    if not SHA256_RE.fullmatch(reviewed_source_sha256):
        raise ValueError("source_sha256 must be a lowercase SHA-256 digest")

    placement = decide_runtime_placement(profile)
    deployment = market.get("deployment") or {}
    endpoint = None
    endpoint_env = None
    if placement["effective"] == "modal-hosted":
        endpoint = validate_https_modal_endpoint(deployment.get("default_endpoint"))
        endpoint_env = require_text(deployment.get("endpoint_env"), "deployment.endpoint_env")
        if not ENV_NAME_RE.fullmatch(endpoint_env):
            raise ValueError("marketplace deployment endpoint_env must be an uppercase env name")

    input_schema = profile["input_schema"]
    output_schema = profile["output_schema"]
    ui = market.get("ui") or {
        "order": [item["field"] for item in profile["form"]],
        "fields": {item["field"]: {"widget": item["widget"]} for item in profile["form"]},
    }
    examples = market.get("examples") or [
        {
            "id": "reviewed-example",
            "title": "Reviewed example",
            "caption": "Complete input",
            "input": profile["happy_path"]["input"],
            "output_preview": "A schema-validated hosted result.",
        }
    ]
    phases = market.get("phases") or [
        {"id": "running", "label": "Running the workflow"},
        {"id": "delivered", "label": "Delivered"},
    ]
    run_manifest = {
        "schema_version": "omo.run-manifest/v1",
        "slug": slug,
        "container_slug": profile["slug"],
        "input_schema_source": f"containers/{profile['slug']}/schemas/input.json",
        "output_schema_source": f"containers/{profile['slug']}/schemas/output.json",
        "input_schema": input_schema,
        "output_schema": output_schema,
        "examples": examples,
        "price_usd": price_usd,
        "chargeable": True,
        "ready": True,
        "phases": phases,
        "ui": ui,
    }

    prompt_name = profile["live"]["prompt"]
    workflow_steps = [
        {
            "type": "llm",
            "role": profile["steps"][0]["id"],
            "model": profile["live"]["default_model"],
            "max_output": int(profile["live"]["max_tokens"]),
            "system": profile["prompts"][prompt_name],
        }
    ]
    workflow_steps.extend(
        {"type": "pipeline", "role": phase["id"], "label": phase["label"]}
        for phase in phases
        if phase["id"] != "delivered"
    )
    catalog = {
        "slug": slug,
        "name": require_text(market.get("title"), "title"),
        "emoji": require_text(market.get("emoji"), "emoji"),
        "category": require_text(market.get("category"), "category"),
        "niche": require_text(market.get("niche"), "niche"),
        "tags": list(market.get("tags") or []),
        "free": bool(market.get("free", False)),
        "priceOwn": float(market.get("price_own", 0)),
        "priceMaintain": float(market.get("price_maintain", 0)),
        "promise": require_text(market.get("promise"), "promise"),
        "maker": require_text(market.get("maker"), "maker"),
        "makerName": require_text(market.get("maker_name"), "maker_name"),
        "version": require_text(market.get("version"), "version"),
        "demoCap": require_text(market.get("demo_cap"), "demo_cap"),
        "desc": require_text(market.get("description"), "description"),
        "cover": market.get("cover"),
        "upvotes": int(market.get("upvotes", 0)),
        "inputs": list(market.get("inputs") or []),
        "outputs": list(market.get("outputs") or []),
        "exampleIn": require_text(market.get("example_in"), "example_in"),
        "exampleOut": list(market.get("example_out") or []),
        "workflow": {"steps": workflow_steps},
        "runPrice": price_usd,
        "runManifest": f"run-manifests/{slug}.json",
        "icon": None,
    }
    runtime = {
        "slug": slug,
        "container_slug": profile["slug"],
        "kind": placement["effective"],
        "reviewed_source_sha256": reviewed_source_sha256,
        "input_schema": input_schema,
        "output_schema": output_schema,
        "run_price_cents": run_price_cents,
    }
    if placement["effective"] == "modal-hosted":
        runtime.update({
            "default_endpoint": endpoint,
            "endpoint_env": endpoint_env,
            "proxy_token_id_env": "HOSTED_MODAL_PROXY_TOKEN_ID",
            "proxy_token_secret_env": "HOSTED_MODAL_PROXY_TOKEN_SECRET",
        })
    else:
        runtime["executor"] = build_worker_executor(profile)
    server_catalog = {
        "slug": slug,
        "name": catalog["name"],
        "license_price_usd": catalog["priceOwn"],
        "run_price_usd": price_usd,
        "model": profile["live"]["default_model"],
        "max_tokens": int(profile["live"]["max_tokens"]),
        "system_prompt": profile["prompts"][prompt_name],
    }
    return {
        "schema_version": "omo.hosted-profile/v1",
        "generator": "tools/host-skill/1.0.0",
        "catalog_managed": bool(market.get("catalog_managed", True)),
        "catalog": catalog,
        "run_manifest": run_manifest,
        "runtime_placement": placement,
        "runtime": runtime,
        "server_catalog": server_catalog,
    }


def discover_hosted_profiles(current: dict[str, Any]) -> list[dict[str, Any]]:
    by_slug: dict[str, dict[str, Any]] = {}
    for path in sorted(CONTAINER_ROOT.glob("*/hosted-profile.json")):
        value = read_json(path)
        by_slug[value["runtime"]["slug"]] = value
    by_slug[current["runtime"]["slug"]] = current
    return [by_slug[slug] for slug in sorted(by_slug)]


def render_registry(profiles: list[dict[str, Any]]) -> str:
    # Profiles generated before runtime placement existed were all Modal. Keep
    # that safe interpretation until each is regenerated explicitly.
    runtime_kinds = {item["runtime"].get("kind", "modal-hosted") for item in profiles}
    unknown_kinds = sorted(runtime_kinds - {"worker-native", "modal-hosted"})
    if unknown_kinds:
        raise ValueError("unsupported generated runtime kind: " + ", ".join(unknown_kinds))
    slugs = [item["runtime"]["slug"] for item in profiles]
    if len(slugs) != len(set(slugs)):
        raise ValueError("duplicate generated runtime slug")
    modal_rows = [[item["runtime"]["slug"], item["runtime"]] for item in profiles if item["runtime"].get("kind", "modal-hosted") == "modal-hosted"]
    worker_rows = [[item["runtime"]["slug"], item["runtime"]] for item in profiles if item["runtime"].get("kind", "modal-hosted") == "worker-native"]
    catalog_rows = [
        [
            item["server_catalog"]["slug"],
            item["server_catalog"]["name"],
            item["server_catalog"]["license_price_usd"],
            item["server_catalog"]["run_price_usd"],
            item["server_catalog"]["model"],
            item["server_catalog"]["max_tokens"],
            item["server_catalog"]["system_prompt"],
        ]
        for item in profiles
    ]
    return (
        "// Generated by tools/host-skill/host.py; do not hand edit.\n"
        "// Contains public contracts and environment-variable names only.\n"
        f"export const HOSTED_WORKER_SKILL_ROWS = {js_json(worker_rows)};\n\n"
        f"export const HOSTED_MODAL_SKILL_ROWS = {js_json(modal_rows)};\n\n"
        f"export const HOSTED_SERVER_CATALOG_ROWS = {js_json(catalog_rows)};\n"
    )


def patch_catalog(source: str, profiles: list[dict[str, Any]]) -> str:
    if (CATALOG_START in source) != (CATALOG_END in source):
        raise ValueError("site/catalog.js has an incomplete host-skill marker pair")
    external_source = re.sub(
        re.escape(CATALOG_START) + r".*?" + re.escape(CATALOG_END),
        "",
        source,
        count=1,
        flags=re.S,
    )
    external_slugs = set(re.findall(r"['\"]?slug['\"]?\s*:\s*['\"]([a-z0-9-]+)['\"]", external_source))
    managed = [
        item for item in profiles
        if item.get("catalog_managed", True) and item["catalog"]["slug"] not in external_slugs
    ]
    lines = [CATALOG_START]
    for item in managed:
        lines.append("  ," + js_json(item["catalog"], 2).lstrip())
    lines.append(CATALOG_END)
    block = "\n".join(lines)
    if CATALOG_START in source:
        patched = re.sub(
            re.escape(CATALOG_START) + r".*?" + re.escape(CATALOG_END),
            lambda _match: block,
            source,
            count=1,
            flags=re.S,
        )
    else:
        array_end = re.search(r"\]\s*;", source)
        if not array_end:
            raise ValueError("site/catalog.js does not contain a catalog array terminator")
        patched = source[:array_end.start()] + block + "\n" + source[array_end.start():]
    return patched.rstrip() + "\n"


def write_or_check(path: Path, content: str, check: bool, drift: list[str]) -> None:
    relative = path.relative_to(ROOT).as_posix()
    if check:
        if not path.is_file() or path.read_text(encoding="utf-8") != content:
            drift.append(relative)
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def register(
    profile: dict[str, Any], out: Path, check: bool
) -> tuple[dict[str, Any], list[str]]:
    manifest = read_json(out / "manifest.json")
    pricing = read_json(out / "pricing-report.json")
    hosted = build_hosted_profile(profile, manifest, pricing)
    profiles = discover_hosted_profiles(hosted)
    catalog_source = CATALOG_PATH.read_text(encoding="utf-8")
    catalog_output = patch_catalog(catalog_source, profiles)
    drift: list[str] = []
    write_or_check(out / "hosted-profile.json", canonical_json(hosted), check, drift)
    write_or_check(
        RUN_MANIFEST_ROOT / f"{hosted['runtime']['slug']}.json",
        canonical_json(hosted["run_manifest"]),
        check,
        drift,
    )
    write_or_check(HOSTED_REGISTRY_PATH, render_registry(profiles), check, drift)
    write_or_check(CATALOG_PATH, catalog_output, check, drift)
    return hosted, drift


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("skill", type=Path, help="Path to the reviewed SKILL.md")
    parser.add_argument("--profile", type=Path, help="Reviewed profile; inferred by skill slug")
    parser.add_argument("--out", type=Path, help="Container output; defaults to containers/<slug>")
    parser.add_argument("--register", action="store_true", help="Generate run manifest, Worker registry, and catalog entry")
    parser.add_argument("--check", action="store_true", help="Fail if generated or registered files drift")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    skill_path = args.skill.resolve()
    skill_text = skill_path.read_text(encoding="utf-8")
    parsed = COMPILER.parse_skill(skill_text)
    slug = parsed["slug"]
    profile_path = (args.profile or PROFILE_ROOT / f"{slug}.json").resolve()
    out = (args.out or CONTAINER_ROOT / slug).resolve()
    profile = read_json(profile_path)

    compiler_command = [
        sys.executable,
        str(COMPILER_PATH),
        str(skill_path),
        "--profile",
        str(profile_path),
        "--out",
        str(out),
    ]
    if args.check:
        compiler_command.append("--check")
    run_checked(compiler_command)

    run_checked(
        [
            sys.executable,
            "-m",
            "pytest",
            "-q",
            "-p",
            "no:cacheprovider",
            str(ROOT / "packages" / "skill-to-modal" / "tests"),
            str(ROOT / "tools" / "host-skill" / "tests"),
        ]
    )
    contract_test = out / "tests" / "test_contract.py"
    run_checked([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", str(contract_test)])
    run_checked(
        [
            "node",
            str(ROOT / "packages" / "skill-to-modal" / "verify-pricing.mjs"),
            slug,
            "--report",
            str(out / "pricing-report.json"),
        ]
    )

    manifest = read_json(out / "manifest.json")
    pricing = read_json(out / "pricing-report.json")
    if manifest["slug"] != slug or pricing["display_price_usd"] != manifest["pricing"]["display_price_usd"]:
        raise ValueError("compiled manifest and pricing report do not agree")

    registered = None
    drift: list[str] = []
    if args.register:
        registered, drift = register(profile, out, args.check)
        if drift:
            print("registration drift: " + ", ".join(drift), file=sys.stderr)
            return 1

    summary = {
        "status": "ready_for_catalog" if manifest["readiness"]["can_submit"] else "blocked",
        "slug": slug,
        "source_sha256": read_json(out / "skill-analysis.json")["source"]["sha256"],
        "manifest": display_path(out / "manifest.json"),
        "price_usd": pricing["display_price_usd"],
        "chargeable": manifest["pricing"]["chargeable"],
        "registered": bool(registered),
        "run_manifest": (
            f"site/run-manifests/{registered['runtime']['slug']}.json" if registered else None
        ),
    }
    print(canonical_json(summary), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
