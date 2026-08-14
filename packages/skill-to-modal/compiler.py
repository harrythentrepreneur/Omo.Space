#!/usr/bin/env python3
"""Deterministically compile a reviewed SKILL.md into a Modal candidate.

The compiler is deliberately data-only: it never imports or executes the
source skill, opens the network, reads credentials, or guesses an unknown
provider operation. A trusted profile supplies explicit contracts and policy
decisions. Complex candidates are emitted with a fail-closed runtime so their
contract can be tested before capabilities are approved.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
import sys
from decimal import Decimal, ROUND_CEILING, ROUND_HALF_UP
from pathlib import Path
from typing import Any


COMPILER_VERSION = "skill-to-modal/0.2.2"
COST_MODEL_PATH = Path(__file__).resolve().parents[2] / "site" / "deploy" / "cost-model.mjs"
ALLOWED_EXECUTION_KINDS = {"single_llm"}
SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def canonical_json(value: Any) -> str:
    return json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True) + "\n"


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def load_cost_model() -> tuple[
    dict[str, dict[str, Decimal]], dict[str, Decimal], Decimal, Decimal, str
]:
    """Read the authoritative repository model instead of maintaining a fork."""
    text = COST_MODEL_PATH.read_text(encoding="utf-8")
    llm_block = text.split("export const LLM_RATES = {", 1)[1].split("};", 1)[0]
    api_block = text.split("export const API_STEP_COSTS = {", 1)[1].split("};", 1)[0]
    llm_rates = {
        model: {"input": Decimal(input_rate), "output": Decimal(output_rate)}
        for model, input_rate, output_rate in re.findall(
            r"'([^']+)'\s*:\s*\{\s*input:\s*([0-9.]+),\s*output:\s*([0-9.]+)\s*\}",
            llm_block,
        )
    }
    api_rates = {
        code: Decimal(rate)
        for code, rate in re.findall(r"^\s*([a-z0-9_]+):\s*([0-9.]+),", api_block, re.M)
    }
    markup_match = re.search(r"export const MARKUP\s*=\s*([0-9.]+)", text)
    floor_match = re.search(r"Math\.max\(withMargin,\s*([0-9.]+)\)", text)
    if not llm_rates or not api_rates or not markup_match or not floor_match:
        raise ValueError("could not parse authoritative site/deploy/cost-model.mjs")
    return (
        llm_rates,
        api_rates,
        Decimal(markup_match.group(1)),
        Decimal(floor_match.group(1)),
        sha256_text(text),
    )


LLM_RATES, API_STEP_COSTS, MARKUP, PRICE_FLOOR, COST_MODEL_SHA256 = load_cost_model()


def slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def parse_frontmatter(text: str) -> dict[str, str]:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        raise ValueError("SKILL.md must begin with YAML frontmatter")
    try:
        end = next(index for index, line in enumerate(lines[1:], 1) if line.strip() == "---")
    except StopIteration as exc:
        raise ValueError("SKILL.md frontmatter is not closed") from exc

    values: dict[str, str] = {}
    for line in lines[1:end]:
        match = re.match(r"^([A-Za-z][A-Za-z0-9_-]*):\s*(.*?)\s*$", line)
        if not match:
            continue
        key, raw = match.groups()
        if raw and raw not in {"|", ">"}:
            values[key] = raw.strip('"\'')
    return values


def extract_steps(text: str) -> list[dict[str, str]]:
    steps: list[dict[str, str]] = []
    in_workflow = False
    for line in text.splitlines():
        heading = re.match(r"^##\s+(.+?)\s*$", line)
        if heading:
            title = heading.group(1).lower()
            if title == "workflow" or title.startswith("the pipeline"):
                in_workflow = True
                continue
            if in_workflow:
                break
        if not in_workflow:
            continue
        match = re.match(r"^(\d+)\.\s+(?:\*\*)?([^:\n*]+)(?:\*\*)?\s*(?::|\()", line)
        if not match:
            continue
        number, title = match.groups()
        normalized = re.sub(r"\s+", " ", title).strip(" .-")
        if normalized:
            steps.append({"number": number, "title": normalized, "id": slugify(normalized)})
    return steps


def detect_needs(text: str) -> list[str]:
    patterns = {
        "deepseek-openai-compatible": r"DeepSeek|deepseek\.ts|DEEPSEEK_API_KEY",
        "ffmpeg": r"\bffmpeg\b|\bffprobe\b",
        "faster-whisper": r"faster-whisper|WhisperModel",
        "ghostscript": r"Ghostscript",
        "headless-chromium": r"headless Chrome|Chromium",
        "hermes-codex-imagegen": r"openai-codex image-gen|Codex OAuth|HERMES VENV",
        "runware": r"Runware|RUNWARE_API_KEY",
    }
    return sorted(name for name, pattern in patterns.items() if re.search(pattern, text, re.I))


def parse_skill(text: str) -> dict[str, Any]:
    frontmatter = parse_frontmatter(text)
    name = frontmatter.get("name", "")
    description = frontmatter.get("description", "")
    if not name or not description:
        raise ValueError("SKILL.md frontmatter requires name and description")
    slug = slugify(name)
    if not SLUG_RE.fullmatch(slug):
        raise ValueError("derived skill slug is invalid")
    return {
        "name": name,
        "slug": slug,
        "description": description,
        "frontmatter": frontmatter,
        "extracted_steps": extract_steps(text),
        "detected_provider_needs": detect_needs(text),
    }


def money(value: Decimal) -> float:
    return float(value.quantize(Decimal("0.00001"), rounding=ROUND_HALF_UP))


def workflow_cost(workflow: dict[str, Any]) -> tuple[Decimal, list[dict[str, Any]]]:
    total = Decimal("0")
    detail: list[dict[str, Any]] = []
    for step in workflow.get("steps", []):
        kind = step.get("type")
        qty = int(step.get("qty", 1))
        if qty < 1:
            raise ValueError("pricing step qty must be positive")
        if kind == "llm":
            model = step.get("model", "deepseek-v4-flash")
            if model not in LLM_RATES:
                raise ValueError(f"unknown pricing model: {model}")
            input_tokens = Decimal(str(step.get("estimated_input_tokens", 0)))
            output_tokens = Decimal(str(step.get("max_output_tokens", 500)))
            rates = LLM_RATES[model]
            unit = input_tokens / Decimal(1_000_000) * rates["input"]
            unit += output_tokens / Decimal(1_000_000) * rates["output"]
            label = f"llm({step.get('role', 'call')})"
        elif kind == "api":
            code = step.get("api")
            if code not in API_STEP_COSTS:
                raise ValueError(f"unknown API cost code: {code}")
            unit = API_STEP_COSTS[code]
            label = f"api({code})"
        else:
            raise ValueError(f"unknown pricing step type: {kind}")
        cost = unit * qty
        total += cost
        detail.append({"step": label, "qty": qty, "cost_usd": money(cost)})
    return total, detail


def price_report(profile: dict[str, Any]) -> dict[str, Any]:
    pricing = profile["pricing"]
    estimates: list[dict[str, Any]] = []
    for estimate in pricing["estimates"]:
        modeled, detail = workflow_cost(estimate["workflow"])
        guard = Decimal(str(estimate.get("guard_cost_usd", "0")))
        guarded = max(modeled, guard)
        modeled_margin = max(modeled * MARKUP, PRICE_FLOOR)
        guarded_margin = max(guarded * MARKUP, PRICE_FLOOR)
        cost_model_price = modeled_margin.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        guarded_price = guarded_margin.quantize(Decimal("0.01"), rounding=ROUND_CEILING)
        estimates.append(
            {
                "tier": estimate["tier"],
                "modeled_cost_usd": money(modeled),
                "guard_cost_usd": money(guard),
                "pricing_cost_usd": money(guarded),
                "cost_model_run_price_usd": float(cost_model_price),
                "guarded_price_floor_usd": float(guarded_price),
                "detail": detail,
                "notes": estimate.get("notes", []),
            }
        )
    default_tier = pricing["default_tier"]
    default = next((row for row in estimates if row["tier"] == default_tier), None)
    if default is None:
        raise ValueError("pricing.default_tier must name an estimate tier")
    return {
        "schema_version": "cognition.pricing/v1",
        "source_model": "site/deploy/cost-model.mjs",
        "rate_snapshot": "repository-2026-08",
        "cost_model_sha256": COST_MODEL_SHA256,
        "markup": float(MARKUP),
        "floor_usd": float(PRICE_FLOOR),
        "quote_status": pricing["quote_status"],
        "chargeable": bool(pricing.get("chargeable", False)),
        "default_tier": default_tier,
        "display_price_usd": default["guarded_price_floor_usd"],
        "estimates": estimates,
        "unpriced_costs": pricing.get("unpriced_costs", []),
        "notes": pricing.get("notes", []),
    }


def live_model_rates(live: dict[str, Any]) -> dict[str, Decimal]:
    """Return live metering rates from the canonical repository cost model."""
    model = str(live.get("default_model") or "").strip()
    if model not in LLM_RATES:
        raise ValueError(f"unknown live model in cost model: {model or '<missing>'}")
    return LLM_RATES[model]


def _relax_flag_controlled_fields(
    schema: dict[str, Any], normalizers: dict[str, Any]
) -> dict[str, Any]:
    """Make fields removed by false input flags optional in generated schemas."""
    relaxed = copy.deepcopy(schema)
    for rule in normalizers.get("flag_fields", []):
        path = rule.get("path") if isinstance(rule, dict) else None
        if not isinstance(path, list) or not path or not all(isinstance(part, str) for part in path):
            raise ValueError("semantic_normalizers.flag_fields paths must be non-empty string lists")
        current = relaxed
        for part in path[:-1]:
            if part == "*":
                current = current.get("items", {})
            else:
                current = current.get("properties", {}).get(part, {})
            if not isinstance(current, dict) or not current:
                raise ValueError("flag-controlled output path is absent from schema: " + ".".join(path))
        field = path[-1]
        if field == "*" or field not in current.get("properties", {}):
            raise ValueError("flag-controlled output field is absent from schema: " + ".".join(path))
        required = current.get("required")
        if isinstance(required, list):
            current["required"] = [name for name in required if name != field]
    return relaxed


def runtime_model_output_schema(profile: dict[str, Any]) -> dict[str, Any]:
    """Return the provider-result schema adjusted for deterministic post-processing."""
    live = profile.get("live")
    if not isinstance(live, dict):
        return {}
    normalizers = profile.get("semantic_normalizers", {})
    if not isinstance(normalizers, dict):
        raise ValueError("semantic_normalizers must be an object")
    return _relax_flag_controlled_fields(live["model_output_schema"], normalizers)


def runtime_output_schema(profile: dict[str, Any]) -> dict[str, Any]:
    """Return the generated wrapper schema, including deterministic post-processing."""
    normalizers = profile.get("semantic_normalizers", {})
    if not isinstance(normalizers, dict):
        raise ValueError("semantic_normalizers must be an object")
    schema = _relax_flag_controlled_fields(profile["output_schema"], normalizers)
    usage = schema.get("properties", {}).get("usage", {})
    llm_calls = usage.get("properties", {}).get("llm_calls")
    if isinstance(llm_calls, dict) and llm_calls.get("const") == 1:
        usage["properties"]["llm_calls"] = {
            "type": "integer",
            "minimum": 1,
            "maximum": 2,
        }
    return schema


def runtime_timeout_seconds(profile: dict[str, Any]) -> int:
    reviewed = int(profile["resources"]["timeout_seconds"])
    live = profile.get("live") if profile.get("readiness", {}).get("can_submit") else None
    if not isinstance(live, dict):
        return reviewed
    return max(reviewed, 2 * int(live.get("timeout_seconds", 120)) + 30)


def modal_app_template(profile: dict[str, Any]) -> str:
    slug = profile["slug"]
    app_name = f"cognition-{slug}"
    version = profile["version"]
    title = profile["name"].replace('"', '\\"')
    apt_chain = ""
    if profile.get("apt_packages"):
        packages = ", ".join(repr(item) for item in profile["apt_packages"])
        apt_chain = f"\n    .apt_install({packages})"
    ready = bool(profile["readiness"]["can_submit"])
    live = profile.get("live") if ready else None
    if live:
        live_rates = live_model_rates(live)
        live_constants = f'''\nLIVE_PROVIDER = {live['provider']!r}
LIVE_BASE_URL_ENV = {live['base_url_env']!r}
LIVE_MODEL_ENV = {live['model_env']!r}
LIVE_API_KEY_ENV = {live['api_key_env']!r}
LIVE_DEFAULT_BASE_URL = {live['default_base_url']!r}
LIVE_DEFAULT_MODEL = {live['default_model']!r}
LIVE_PROMPT_PATH = {('prompts/' + live['prompt'])!r}
LIVE_MAX_TOKENS = {int(live['max_tokens'])}
LIVE_TEMPERATURE = {float(live['temperature'])!r}
LIVE_TIMEOUT_SECONDS = {int(live.get('timeout_seconds', 120))}
LIVE_INPUT_RATE_PER_MILLION = {float(live_rates['input'])!r}
LIVE_OUTPUT_RATE_PER_MILLION = {float(live_rates['output'])!r}
LIVE_MODEL_OUTPUT_SCHEMA = {runtime_model_output_schema(profile)!r}
SEMANTIC_NORMALIZERS = {profile.get('semantic_normalizers', {})!r}
'''
        live_executor = '''

def _extract_json_object(value: str) -> dict[str, Any]:
    fenced = re.sub(r"^```(?:json)?\\s*|\\s*```$", "", value.strip(), flags=re.I)
    parsed = json.loads(fenced)
    if not isinstance(parsed, dict):
        raise ValueError("provider output must be a JSON object")
    return parsed


_ALIAS_GROUPS = (
    {"count", "number", "total"},
    {"input", "text", "source"},
    {"text", "digraph", "grapheme", "pattern"},
    {"word", "token"},
    {"syllabified", "syllables", "split"},
    {"ambiguity", "ambiguity_note", "note", "notes"},
    {"possible_confusions", "confusion_labels", "confusions", "labels"},
    {"practice_suggestions", "practice_ideas", "practice"},
    {"observation", "hypothesis"},
    {"premise", "story", "story_idea", "logline"},
    {"writing_hook", "hook"},
    {"rules_explanation", "rules", "explanation"},
    {"example_words", "examples"},
    {"target_words", "words"},
    {"sight_or_irregular_words", "sight_words", "irregular_words"},
    {"matched_phonemes", "phonemes"},
    {"target_position", "position"},
    {"pronunciation_note", "note", "notes"},
    {"rule", "phonics_rule", "phonics_pattern", "pattern"},
    {"constraints_used", "constraints"},
)


def _key_tokens(value: str) -> set[str]:
    words = re.findall(r"[a-z0-9]+", re.sub(r"([a-z])([A-Z])", r"\\1_\\2", value).lower())
    return {word[:-1] if word.endswith("s") and len(word) > 3 else word for word in words}


def _schema_types(schema: dict[str, Any]) -> set[str]:
    declared = schema.get("type")
    if isinstance(declared, str):
        return {declared}
    if isinstance(declared, list):
        return {str(item) for item in declared}
    if "const" in schema:
        value = schema["const"]
        if isinstance(value, bool):
            return {"boolean"}
        if isinstance(value, int):
            return {"integer"}
        if isinstance(value, str):
            return {"string"}
    if isinstance(schema.get("enum"), list) and schema["enum"]:
        return _schema_types({"const": schema["enum"][0]})
    return set()


def _value_type(value: Any) -> str:
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "number"
    if isinstance(value, str):
        return "string"
    if isinstance(value, list):
        return "array"
    if isinstance(value, dict):
        return "object"
    return "null"


def _alias_score(source: str, target: str, value: Any, schema: dict[str, Any]) -> int:
    if source == target:
        return 1000
    source_tokens = _key_tokens(source)
    target_tokens = _key_tokens(target)
    score = 0
    if source_tokens and target_tokens:
        overlap = source_tokens & target_tokens
        if overlap:
            score = max(score, 72 + 4 * len(overlap))
        if source_tokens <= target_tokens or target_tokens <= source_tokens:
            score = max(score, 82)
    for group in _ALIAS_GROUPS:
        group_tokens = set().union(*(_key_tokens(item) for item in group))
        if source_tokens & group_tokens and target_tokens & group_tokens:
            score = max(score, 68)
    expected = _schema_types(schema)
    actual = _value_type(value)
    if actual in expected or (actual == "integer" and "number" in expected):
        score += 8
    elif expected:
        coercible = actual == "string" and (
            "array" in expected
            or ("integer" in expected and bool(re.fullmatch(r"[-+]?\\d+", value.strip())))
            or ("number" in expected and bool(re.fullmatch(r"[-+]?(?:\\d+(?:\\.\\d*)?|\\.\\d+)", value.strip())))
            or ("boolean" in expected and value.strip().lower() in {"true", "false", "yes", "no", "1", "0"})
        )
        if not coercible:
            score -= 30
    return score


def _default_required(
    name: str,
    schema: dict[str, Any],
    context: dict[str, Any],
    repaired: dict[str, Any],
) -> tuple[bool, Any]:
    if "const" in schema:
        return True, schema["const"]
    if name == "type":
        requested = context.get("digraph_type")
        if requested in {"consonant", "vowel"}:
            return True, requested
        text = str(repaired.get("text") or "").lower()
        vowel_digraphs = {"ai", "au", "aw", "ay", "ea", "ee", "ew", "ie", "oa", "oe", "oi", "oo", "ou", "ow", "oy", "ue", "ui"}
        if text:
            return True, "vowel" if text in vowel_digraphs else "consonant"
    candidates = sorted(
        (
            (_alias_score(source, name, value, schema), source, value)
            for source, value in context.items()
        ),
        reverse=True,
    )
    if candidates and candidates[0][0] >= 68:
        return True, candidates[0][2]
    if name.endswith("_count"):
        prefix = _key_tokens(name.removesuffix("_count"))
        for sibling, value in repaired.items():
            if isinstance(value, list) and prefix & _key_tokens(sibling):
                return True, len(value)
    if name == "word" and isinstance(context.get("text"), str):
        start, end = repaired.get("start"), repaired.get("end")
        if isinstance(start, int) and isinstance(end, int):
            source_text = context["text"]
            left, right = start, end
            while left > 0 and (source_text[left - 1].isalnum() or source_text[left - 1] in "'-"):
                left -= 1
            while right < len(source_text) and (source_text[right].isalnum() or source_text[right] in "'-"):
                right += 1
            if left < right:
                return True, source_text[left:right]
    if name == "target_position":
        word = str(repaired.get("word") or "").lower()
        matches = repaired.get("matched_phonemes")
        if word and isinstance(matches, list):
            positions: set[str] = set()
            for match in matches:
                needle = str(match).lower()
                index = word.find(needle)
                if index < 0:
                    continue
                if word.find(needle, index + 1) >= 0:
                    positions.add("multiple")
                elif index == 0:
                    positions.add("initial")
                elif index + len(needle) == len(word):
                    positions.add("final")
                else:
                    positions.add("medial")
            if positions:
                return True, sorted(positions)[0] if len(positions) == 1 else "multiple"
    if name == "target_words":
        source = context.get("__generated__")
        coverage = source.get("coverage") if isinstance(source, dict) else None
        sentence = str(repaired.get("text") or "").lower()
        if isinstance(coverage, dict) and sentence:
            words: list[str] = []
            for covered in coverage.values():
                if not isinstance(covered, list):
                    continue
                for word in covered:
                    text = str(word)
                    if re.search(r"(?<![A-Za-z])" + re.escape(text.lower()) + r"(?![A-Za-z])", sentence):
                        words.append(text)
            if words:
                return True, words
    if name == "explanation" and isinstance(repaired.get("observation"), str):
        return True, repaired["observation"]
    if name == "uncertainty":
        dialect = str(context.get("dialect") or "the selected dialect")
        return True, f"Pronunciation may vary by speaker in {dialect}; review before teaching."
    if name in {"note", "pronunciation_note"}:
        dialect = str(context.get("dialect") or "the selected dialect")
        return True, f"Review this example in {dialect}."
    if name == "ambiguity_note":
        return True, ""
    if name == "writing_hook" and isinstance(repaired.get("premise"), str):
        premise = repaired["premise"].strip()
        if premise:
            return True, ("What happens next? " + premise)[:240]
    expected = _schema_types(schema)
    if "array" in expected and int(schema.get("minItems", 0)) == 0:
        return True, []
    if "string" in expected and int(schema.get("minLength", 0)) == 0:
        return True, ""
    if "object" in expected and not schema.get("required"):
        return True, {}
    return False, None


def _coerce_to_schema(value: Any, schema: dict[str, Any], context: dict[str, Any]) -> Any:
    expected = _schema_types(schema)
    if "object" in expected:
        properties = schema.get("properties") if isinstance(schema.get("properties"), dict) else {}
        if not isinstance(value, dict):
            seed: dict[str, Any] = {}
            for preferred in ("text", "word", "answer", "title", "premise", "value"):
                if preferred in properties:
                    seed[preferred] = value
                    break
            value = seed
        repaired: dict[str, Any] = {}
        used_sources: set[str] = set()
        for name, child_schema in properties.items():
            if name in value:
                repaired[name] = _coerce_to_schema(value[name], child_schema, context)
                used_sources.add(name)
        for source, child_value in value.items():
            if source in used_sources:
                continue
            choices = sorted(
                (
                    (_alias_score(source, target, child_value, child_schema), target, child_schema)
                    for target, child_schema in properties.items()
                    if target not in repaired
                ),
                reverse=True,
            )
            if choices and choices[0][0] >= 68:
                _, target, child_schema = choices[0]
                repaired[target] = _coerce_to_schema(child_value, child_schema, context)
        for name in schema.get("required", []):
            if name in repaired or name not in properties:
                continue
            found, default = _default_required(name, properties[name], context, repaired)
            if found:
                repaired[name] = _coerce_to_schema(default, properties[name], context)
        for name, child_schema in properties.items():
            allowed = child_schema.get("enum") if isinstance(child_schema, dict) else None
            if name in repaired and isinstance(allowed, list) and repaired[name] not in allowed:
                found, default = _default_required(name, child_schema, context, repaired)
                if found:
                    repaired[name] = _coerce_to_schema(default, child_schema, context)
        return repaired
    if "array" in expected:
        item_schema = schema.get("items") if isinstance(schema.get("items"), dict) else {}
        if isinstance(value, dict) and "object" not in _schema_types(item_schema):
            value = list(value)
        elif not isinstance(value, list):
            if isinstance(value, str) and re.search(r"[,;\\n]", value):
                value = [part.strip() for part in re.split(r"[,;\\n]+", value) if part.strip()]
            else:
                value = [value]
        repaired_items = [_coerce_to_schema(item, item_schema, context) for item in value]
        if schema.get("uniqueItems"):
            unique: list[Any] = []
            seen: set[str] = set()
            for item in repaired_items:
                marker = json.dumps(item, ensure_ascii=False, sort_keys=True)
                if marker not in seen:
                    seen.add(marker)
                    unique.append(item)
            repaired_items = unique
        maximum = schema.get("maxItems")
        return repaired_items[: int(maximum)] if isinstance(maximum, int) else repaired_items
    if "integer" in expected:
        if isinstance(value, str) and re.fullmatch(r"[-+]?\\d+", value.strip()):
            return int(value.strip())
        if isinstance(value, float) and value.is_integer():
            return int(value)
        return value
    if "number" in expected:
        if isinstance(value, str):
            try:
                return float(value.strip())
            except ValueError:
                return value
        return value
    if "boolean" in expected and isinstance(value, str):
        if value.strip().lower() in {"true", "yes", "1"}:
            return True
        if value.strip().lower() in {"false", "no", "0"}:
            return False
    if "string" in expected:
        if value is None and int(schema.get("minLength", 0)) == 0:
            value = ""
        elif isinstance(value, list) and all(not isinstance(item, (dict, list)) for item in value):
            value = ", ".join(str(item) for item in value)
        elif not isinstance(value, str) and value is not None:
            value = str(value)
        maximum = schema.get("maxLength")
        if isinstance(value, str) and isinstance(maximum, int):
            value = value[:maximum]
        minimum = schema.get("minLength")
        if isinstance(value, str) and isinstance(minimum, int) and len(value) < minimum:
            suffix = " Review the supplied context and dialect before teaching."
            value = (value + suffix)[: int(schema.get("maxLength", len(value) + len(suffix)))]
    return value


def _repair_to_schema(
    generated: dict[str, Any], schema: dict[str, Any], prompt_input: dict[str, Any]
) -> dict[str, Any]:
    context = dict(prompt_input)
    context["__generated__"] = generated
    repaired = _coerce_to_schema(generated, schema, context)
    return repaired if isinstance(repaired, dict) else {}


def _strip_output_path(value: Any, path: list[str]) -> None:
    if not path:
        return
    part = path[0]
    if part == "*":
        if isinstance(value, list):
            for item in value:
                _strip_output_path(item, path[1:])
        return
    if not isinstance(value, dict) or part not in value:
        return
    if len(path) == 1:
        value.pop(part, None)
        return
    _strip_output_path(value[part], path[1:])


def _output_path_exists(value: Any, path: list[str]) -> bool:
    if not path:
        return True
    part = path[0]
    if part == "*":
        return isinstance(value, list) and any(_output_path_exists(item, path[1:]) for item in value)
    return isinstance(value, dict) and part in value and _output_path_exists(value[part], path[1:])


def _containing_word(source: str, start: int, end: int) -> str:
    left, right = start, end
    while left > 0 and (source[left - 1].isalnum() or source[left - 1] in "'-"):
        left -= 1
    while right < len(source) and (source[right].isalnum() or source[right] in "'-"):
        right += 1
    return source[left:right]


def _reviewed_digraph_occurrences(
    payload: dict[str, Any], generated: dict[str, Any]
) -> list[dict[str, Any]]:
    config = SEMANTIC_NORMALIZERS.get("digraph_spans")
    if not isinstance(config, dict):
        return []
    source = str(payload.get("text") or "")
    requested = str(payload.get("digraph_type") or "all")
    include_explanations = payload.get("include_explanations") is not False
    prose: dict[tuple[str, str], list[str]] = {}
    for item in generated.get("occurrences", []):
        if not isinstance(item, dict):
            continue
        explanation = item.get("explanation")
        token = str(item.get("text") or "").lower()
        word = str(item.get("word") or "").lower()
        if include_explanations and isinstance(explanation, str) and explanation.strip() and token:
            prose.setdefault((token, word), []).append(explanation)

    kinds = ("consonant", "vowel") if requested == "all" else (requested,)
    occurrences: list[dict[str, Any]] = []
    seen: set[tuple[int, int, str]] = set()
    lower_source = source.lower()
    for kind in kinds:
        reviewed = config.get(kind, [])
        if not isinstance(reviewed, list):
            continue
        for raw_token in reviewed:
            token = str(raw_token).lower()
            if not token:
                continue
            start = 0
            while True:
                start = lower_source.find(token, start)
                if start < 0:
                    break
                end = start + len(token)
                marker = (start, end, kind)
                if marker not in seen:
                    seen.add(marker)
                    word = _containing_word(source, start, end)
                    occurrence: dict[str, Any] = {
                        "text": source[start:end],
                        "word": word,
                        "start": start,
                        "end": end,
                        "type": kind,
                    }
                    available = prose.get((token, word.lower()), [])
                    if include_explanations and available:
                        occurrence["explanation"] = available.pop(0)
                    occurrences.append(occurrence)
                start += 1
    return sorted(
        occurrences,
        key=lambda item: (item["start"], item["end"], item["type"], item["text"].lower()),
    )


def _variant_index(word: str, variant: str) -> tuple[int, int] | None:
    clean_word = re.sub(r"[^a-z]", "", word.lower())
    clean_variant = variant.lower()
    if "_" in clean_variant:
        pieces = [re.sub(r"[^a-z]", "", piece) for piece in clean_variant.split("_")]
        pieces = [piece for piece in pieces if piece]
        if not pieces:
            return None
        match = re.search(".*?".join(re.escape(piece) for piece in pieces), clean_word)
        return (match.start(), match.end()) if match else None
    needle = re.sub(r"[^a-z]", "", clean_variant)
    start = clean_word.find(needle) if needle else -1
    return (start, start + len(needle)) if start >= 0 else None


def _matching_requested_phonemes(
    word: str, requested: list[str], phoneme_map: dict[str, Any]
) -> tuple[list[str], list[tuple[int, int]]]:
    matched: list[str] = []
    spans: list[tuple[int, int]] = []
    for raw_phoneme in requested:
        phoneme = str(raw_phoneme)
        variants = phoneme_map.get(phoneme.lower(), [phoneme])
        if not isinstance(variants, list):
            variants = [phoneme]
        found = next(
            (span for variant in variants if (span := _variant_index(word, str(variant))) is not None),
            None,
        )
        if found is not None:
            matched.append(phoneme)
            spans.append(found)
    return matched, spans


def _phoneme_target_position(word: str, spans: list[tuple[int, int]]) -> str:
    clean_length = len(re.sub(r"[^a-z]", "", word.lower()))
    if len(spans) != 1:
        return "multiple"
    start, end = spans[0]
    if start == 0:
        return "initial"
    if end == clean_length:
        return "final"
    return "medial"


def _append_bounded_warning(generated: dict[str, Any], warning: str) -> None:
    schema = LIVE_MODEL_OUTPUT_SCHEMA.get("properties", {}).get("warnings", {})
    maximum = int(schema.get("maxItems", 0))
    if maximum <= 0:
        return
    warnings = [str(item) for item in generated.get("warnings", []) if str(item).strip()]
    if warning in warnings:
        generated["warnings"] = warnings[:maximum]
        return
    generated["warnings"] = (warnings[: maximum - 1] + [warning]) if len(warnings) >= maximum else warnings + [warning]


def _normalize_phoneme_containment(
    generated: dict[str, Any], payload: dict[str, Any]
) -> None:
    config = SEMANTIC_NORMALIZERS.get("phoneme_containment")
    if not isinstance(config, dict):
        return
    requested = [str(item) for item in payload.get("phonemes", [])]
    phoneme_map = config.get("phoneme_to_graphemes", {})
    if not isinstance(phoneme_map, dict):
        phoneme_map = {}
    kept: list[dict[str, Any]] = []
    removed = 0
    for item in generated.get("words", []):
        if not isinstance(item, dict):
            removed += 1
            continue
        word = str(item.get("word") or "")
        matched, spans = _matching_requested_phonemes(word, requested, phoneme_map)
        if not matched:
            removed += 1
            continue
        item["matched_phonemes"] = matched
        item["target_position"] = _phoneme_target_position(word, spans)
        kept.append(item)
    generated["words"] = kept
    generated["coverage"] = [
        phoneme
        for phoneme in requested
        if any(phoneme in item.get("matched_phonemes", []) for item in kept)
    ]
    if removed:
        _append_bounded_warning(
            generated,
            f"Removed {removed} word{'s' if removed != 1 else ''} without a reviewed grapheme for the requested phonemes.",
        )


def _semantic_normalize(
    generated: dict[str, Any], payload: dict[str, Any]
) -> dict[str, Any]:
    if isinstance(SEMANTIC_NORMALIZERS.get("digraph_spans"), dict):
        generated["occurrences"] = _reviewed_digraph_occurrences(payload, generated)
        generated["summary"] = list(
            dict.fromkeys(item["text"].lower() for item in generated["occurrences"])
        )
    _normalize_phoneme_containment(generated, payload)
    for rule in SEMANTIC_NORMALIZERS.get("flag_fields", []):
        if isinstance(rule, dict) and payload.get(rule.get("flag")) is False:
            _strip_output_path(generated, rule.get("path", []))
    return generated


def _semantic_validation_diff(
    generated: dict[str, Any], payload: dict[str, Any]
) -> str:
    details: list[str] = []
    if isinstance(SEMANTIC_NORMALIZERS.get("digraph_spans"), dict):
        expected = _reviewed_digraph_occurrences(payload, {})
        fields = ("text", "word", "start", "end", "type")
        expected_signatures = [tuple(item.get(field) for field in fields) for item in expected]
        actual_signatures = [
            tuple(item.get(field) for field in fields)
            for item in generated.get("occurrences", [])
            if isinstance(item, dict)
        ]
        if actual_signatures != expected_signatures:
            details.append(
                "$.occurrences:semantic_source_spans(expected="
                + str(len(expected_signatures))
                + ",actual="
                + str(len(actual_signatures))
                + ")"
            )
        expected_summary = list(dict.fromkeys(item["text"].lower() for item in expected))
        if generated.get("summary") != expected_summary:
            details.append("$.summary:semantic_digraph_coverage")

    config = SEMANTIC_NORMALIZERS.get("phoneme_containment")
    if isinstance(config, dict):
        requested = [str(item) for item in payload.get("phonemes", [])]
        phoneme_map = config.get("phoneme_to_graphemes", {})
        words = generated.get("words", [])
        if len(words) != payload.get("word_count"):
            details.append(
                "$.words:semantic_word_count(expected="
                + str(payload.get("word_count"))
                + ",actual="
                + str(len(words))
                + ")"
            )
        covered: set[str] = set()
        for item in words:
            matched, _spans = _matching_requested_phonemes(
                str(item.get("word") or ""), requested, phoneme_map
            )
            if item.get("matched_phonemes") != matched or not matched:
                details.append("$.words:semantic_phoneme_containment")
                break
            covered.update(matched)
        if any(phoneme not in covered for phoneme in requested):
            details.append("$.coverage:semantic_requested_phonemes")

    for rule in SEMANTIC_NORMALIZERS.get("flag_fields", []):
        if not isinstance(rule, dict) or payload.get(rule.get("flag")) is not False:
            continue
        path = rule.get("path", [])
        if _output_path_exists(generated, path):
            details.append("$" + "".join("[*]" if part == "*" else "." + part for part in path) + ":flag_disabled")
    return ";".join(dict.fromkeys(details))


def _validation_diff(instance: Any, schema: dict[str, Any]) -> str:
    errors = sorted(
        Draft202012Validator(schema).iter_errors(instance),
        key=lambda error: (list(error.absolute_path), str(error.validator)),
    )
    details: list[str] = []
    for error in errors[:20]:
        path = "$" + "".join(
            f"[{part}]" if isinstance(part, int) else f".{part}" for part in error.absolute_path
        )
        if error.validator == "required" and isinstance(error.instance, dict):
            missing = [name for name in error.validator_value if name not in error.instance]
            detail = "required(" + ",".join(missing) + ")"
        elif error.validator == "additionalProperties" and isinstance(error.instance, dict):
            allowed = set(error.schema.get("properties", {}))
            extra_count = sum(1 for name in error.instance if name not in allowed)
            detail = f"additionalProperties(count={extra_count})"
        elif error.validator == "type":
            detail = "type(expected=" + str(error.validator_value) + ")"
        elif error.validator in {"minLength", "maxLength", "minItems", "maxItems", "minimum", "maximum", "enum", "const", "uniqueItems"}:
            detail = str(error.validator) + "(expected=" + str(error.validator_value)[:160] + ")"
        else:
            detail = str(error.validator)
        details.append(path + ":" + detail)
    if len(errors) > 20:
        details.append(f"...+{len(errors) - 20}_more")
    return ";".join(details)


def _provider_request(
    base_url: str,
    model: str,
    messages: list[dict[str, str]],
) -> tuple[str, dict[str, Any]]:
    request_body = {
        "model": model,
        "messages": messages,
        "temperature": LIVE_TEMPERATURE,
        "max_tokens": LIVE_MAX_TOKENS,
        "response_format": {"type": "json_object"},
        "thinking": {"type": "disabled"},
    }
    request = urllib.request.Request(
        base_url + "/chat/completions",
        data=json.dumps(request_body).encode("utf-8"),
        headers={
            "Authorization": "Bearer " + os.environ[LIVE_API_KEY_ENV],
            "Content-Type": "application/json",
            "User-Agent": "Omo-Skill-Runner/0.2",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=LIVE_TIMEOUT_SECONDS) as response:
            raw = response.read(2_000_001)
    except urllib.error.HTTPError as exc:
        raise ProviderCallError(f"LLM_HTTP_{exc.code}") from exc
    except (urllib.error.URLError, TimeoutError) as exc:
        raise ProviderCallError("LLM_UNAVAILABLE") from exc
    if len(raw) > 2_000_000:
        raise ProviderCallError("LLM_RESPONSE_TOO_LARGE")
    try:
        provider_response = json.loads(raw)
        content = str(provider_response["choices"][0]["message"]["content"])
    except Exception as exc:
        raise ProviderCallError("LLM_RESPONSE_INVALID") from exc
    return content, provider_response


def _candidate(
    content: str, payload: dict[str, Any]
) -> tuple[dict[str, Any] | None, str]:
    try:
        parsed = _extract_json_object(content)
    except Exception:
        return None, "$:invalid_json"
    repaired = _repair_to_schema(parsed, LIVE_MODEL_OUTPUT_SCHEMA, payload)
    normalized = _semantic_normalize(repaired, payload)
    diffs = [
        _validation_diff(normalized, LIVE_MODEL_OUTPUT_SCHEMA),
        _semantic_validation_diff(normalized, payload),
    ]
    return normalized, ";".join(diff for diff in diffs if diff)


def _provider_completion(payload: dict[str, Any]) -> dict[str, Any]:
    missing = [name for name in readiness()["required_env_names"] if not os.environ.get(name)]
    if missing:
        raise WorkflowNotReady("MISSING_REQUIRED_ENV:" + ",".join(sorted(missing)))

    base_url = os.environ[LIVE_BASE_URL_ENV].rstrip("/")
    if not base_url.startswith("https://"):
        raise WorkflowNotReady("LLM_BASE_URL_MUST_BE_HTTPS")
    model = os.environ[LIVE_MODEL_ENV]
    system_prompt = (_asset_root() / LIVE_PROMPT_PATH).read_text(encoding="utf-8").strip()
    schema_contract = json.dumps(
        LIVE_MODEL_OUTPUT_SCHEMA, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )
    system_prompt += (
        "\\n\\nOUTPUT CONTRACT (mandatory): Return exactly one JSON object matching this "
        "JSON Schema. Use exactly the declared field names and types, include every "
        "required field, and include no undeclared fields:\\n" + schema_contract
    )
    user_prompt = "Run the reviewed workflow using only this JSON input:\\n" + json.dumps(
        payload, ensure_ascii=False, sort_keys=True
    )
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]
    content, first_response = _provider_request(base_url, model, messages)
    generated, validation_diff = _candidate(content, payload)
    responses = [first_response]
    if validation_diff:
        corrective = (
            "CORRECTIVE RETRY (final attempt): the previous JSON failed validation. "
            "Fix exactly these schema violations: " + validation_diff + ". "
            "Return the complete corrected JSON object only; use the exact schema in "
            "the system instruction and invent no fields. Do not repeat or quote "
            "input values, credentials, prior response text, or undeclared field names."
        )
        try:
            retry_content, retry_response = _provider_request(
                base_url,
                model,
                messages + [{"role": "user", "content": corrective}],
            )
        except ProviderCallError as exc:
            raise ProviderCallError(
                "LLM_INVALID_OUTPUT:" + validation_diff + ";retry=" + str(exc)
            ) from exc
        responses.append(retry_response)
        generated, retry_diff = _candidate(retry_content, payload)
        if retry_diff or generated is None:
            raise ProviderCallError("LLM_INVALID_OUTPUT:" + (retry_diff or "$:invalid_json"))
    if generated is None:
        raise ProviderCallError("LLM_INVALID_OUTPUT:" + (validation_diff or "$:unknown"))

    prompt_tokens = sum(max(0, int((response.get("usage") or {}).get("prompt_tokens") or 0)) for response in responses)
    completion_tokens = sum(max(0, int((response.get("usage") or {}).get("completion_tokens") or 0)) for response in responses)
    estimated_cost = (
        prompt_tokens * LIVE_INPUT_RATE_PER_MILLION
        + completion_tokens * LIVE_OUTPUT_RATE_PER_MILLION
    ) / 1_000_000
    return {
        "run_id": "run-" + str(uuid.uuid4()),
        "status": "completed",
        "workflow_version": WORKFLOW_VERSION,
        **generated,
        "usage": {
            "provider": LIVE_PROVIDER,
            "model": str(responses[-1].get("model") or model),
            "llm_calls": len(responses),
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "estimated_cost_usd": round(estimated_cost, 8),
        },
    }
'''
        secret_arg = f",\n    secrets=[modal.Secret.from_name({live['modal_secret_name']!r})]"
    else:
        live_constants = ""
        live_executor = ""
        secret_arg = ""
    return f'''"""Generated Modal contract runtime for {title}.

Generated by {COMPILER_VERSION}; change the profile/compiler, not this file.
Complex or unapproved capabilities fail closed. Tests inject a pure mock
executor and never make provider calls.
"""

from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
import uuid
from functools import lru_cache
from pathlib import Path
from typing import Any, Callable

import modal
from jsonschema import Draft202012Validator


APP_NAME = {app_name!r}
WORKFLOW_VERSION = {slug + '@' + version!r}
EXECUTION_KIND = {profile['execution_kind']!r}
LOCAL_ROOT = Path(__file__).resolve().parent
IMAGE_ROOT = Path({('/root/' + slug.replace('-', '_'))!r})
{live_constants}


class WorkflowNotReady(RuntimeError):
    """Raised before spend when the reviewed workflow cannot run live."""


class ProviderCallError(RuntimeError):
    """Safe provider failure code; response bodies and credentials are never logged."""


def _asset_root() -> Path:
    return LOCAL_ROOT if (LOCAL_ROOT / "schemas" / "input.json").is_file() else IMAGE_ROOT


@lru_cache(maxsize=None)
def load_json(relative_path: str) -> dict[str, Any]:
    with (_asset_root() / relative_path).open(encoding="utf-8") as handle:
        return json.load(handle)


@lru_cache(maxsize=None)
def load_schema(name: str) -> dict[str, Any]:
    schema = load_json(f"schemas/{{name}}")
    Draft202012Validator.check_schema(schema)
    return schema


def validate_instance(instance: Any, schema_name: str) -> None:
    Draft202012Validator(load_schema(schema_name)).validate(instance)


def readiness() -> dict[str, Any]:
    return load_json("manifest.json")["readiness"]
{live_executor}


Executor = Callable[[dict[str, Any]], dict[str, Any]]


def execute_workflow(
    payload: dict[str, Any], *, executor: Executor | None = None
) -> dict[str, Any]:
    """Validate, execute once, and validate output.

    A mock executor is an explicit offline test seam. The generated live
    candidate never substitutes mock artifacts for unavailable providers.
    """
    validate_instance(payload, "input.json")
    if executor is None:
        state = readiness()
        if not state["can_submit"]:
            raise WorkflowNotReady(
                "; ".join(reason["code"] for reason in state["blockers"])
            )
        executor = _provider_completion
    result = executor(payload)
    validate_instance(result, "output.json")
    return result


runtime_image = (
    modal.Image.debian_slim(python_version="3.12"){apt_chain}
    .uv_pip_install(
        "modal==1.5.0",
        "fastapi==0.109.0",
        "jsonschema==4.26.0",
    )
    .add_local_dir(LOCAL_ROOT / "schemas", IMAGE_ROOT / "schemas", copy=True)
    .add_local_dir(LOCAL_ROOT / "prompts", IMAGE_ROOT / "prompts", copy=True)
    .add_local_file(LOCAL_ROOT / "manifest.json", str(IMAGE_ROOT / "manifest.json"), copy=True)
)

app = modal.App(APP_NAME)


@app.function(
    image=runtime_image,
    cpu={profile['resources']['cpu']},
    memory={profile['resources']['memory_mb']},
    timeout={runtime_timeout_seconds(profile)},
    min_containers=0,
    max_containers={profile['resources']['max_containers']},
    scaledown_window=5{secret_arg},
)
def run_workflow(payload: dict[str, Any]) -> dict[str, Any]:
    return execute_workflow(payload)


SpawnRunner = Callable[[dict[str, Any]], str]
LookupResult = Callable[[str], dict[str, Any]]


def create_fastapi_app(
    spawn_runner: SpawnRunner | None = None,
    lookup_result: LookupResult | None = None,
    *,
    ready_override: bool | None = None,
) -> Any:
    from fastapi import Body, FastAPI, HTTPException
    from fastapi.responses import JSONResponse
    from jsonschema import ValidationError

    web = FastAPI(title={title!r}, version={version!r})

    def default_spawn(payload: dict[str, Any]) -> str:
        return run_workflow.spawn(payload).object_id

    def default_lookup(call_id: str) -> dict[str, Any]:
        return modal.FunctionCall.from_id(call_id).get(timeout=0)

    spawn = spawn_runner or default_spawn
    lookup = lookup_result or default_lookup

    @web.post("/v1/runs", status_code=202)
    async def submit(body: Any = Body(...)) -> Any:
        try:
            validate_instance(body, "input.json")
        except ValidationError as exc:
            raise HTTPException(status_code=422, detail=exc.message) from exc

        state = readiness()
        can_submit = state["can_submit"] if ready_override is None else ready_override
        if not can_submit:
            return JSONResponse(
                {{
                    "status": "not_ready",
                    "error": {{
                        "code": "WORKFLOW_NOT_READY",
                        "blockers": state["blockers"],
                    }},
                }},
                status_code=503,
            )

        call_id = spawn(body)
        run_id = str(uuid.uuid4())
        return {{
            "run_id": run_id,
            "call_id": call_id,
            "status": "accepted",
            "result_url": f"/v1/runs/{{call_id}}",
        }}

    @web.get("/v1/runs/{{call_id}}")
    async def get_result(call_id: str) -> Any:
        try:
            result = lookup(call_id)
            validate_instance(result, "output.json")
            return result
        except TimeoutError:
            return JSONResponse({{"call_id": call_id, "status": "running"}}, status_code=202)
        except Exception:
            return JSONResponse(
                {{"call_id": call_id, "status": "failed", "error": {{"code": "RUN_FAILED"}}}},
                status_code=500,
            )

    return web


@app.function(
    image=runtime_image,
    min_containers=0,
    max_containers=20,
    scaledown_window=2,
)
@modal.concurrent(max_inputs=20)
@modal.asgi_app(requires_proxy_auth=True)
def api() -> Any:
    return create_fastapi_app()
'''


def contract_test_template(profile: dict[str, Any]) -> str:
    module_name = profile["slug"].replace("-", "_")
    expected_ready = bool(profile["readiness"]["can_submit"])
    expected_chargeable = bool(profile["pricing"].get("chargeable", False)) if expected_ready else False
    return f'''"""Generated offline contract tests: no keys, network, or spend."""

from __future__ import annotations

import asyncio
import importlib.util
import json
import os
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[1]
CASES = json.loads((ROOT / "tests" / "cases.json").read_text(encoding="utf-8"))


def _load_module():
    spec = importlib.util.spec_from_file_location({(module_name + '_modal_app')!r}, ROOT / "modal_app.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


modal_app = _load_module()


def _schema(name: str) -> dict:
    return json.loads((ROOT / "schemas" / name).read_text(encoding="utf-8"))


INPUT_SCHEMA = _schema("input.json")
OUTPUT_SCHEMA = _schema("output.json")
EXPECTED_READY = {expected_ready!r}
EXPECTED_CHARGEABLE = {expected_chargeable!r}


def _route(web, path: str):
    return next(route for route in web.routes if route.path == path)


def test_schema_documents_are_valid_draft_2020_12() -> None:
    Draft202012Validator.check_schema(INPUT_SCHEMA)
    Draft202012Validator.check_schema(OUTPUT_SCHEMA)


def test_happy_fixture_matches_both_contracts() -> None:
    Draft202012Validator(INPUT_SCHEMA).validate(CASES["happy_path"]["input"])
    Draft202012Validator(OUTPUT_SCHEMA).validate(CASES["happy_path"]["output"])


@pytest.mark.parametrize("case", CASES["negative_cases"], ids=lambda case: case["id"])
def test_negative_inputs_are_rejected(case: dict) -> None:
    assert list(Draft202012Validator(INPUT_SCHEMA).iter_errors(case["input"])), case["reason"]


def test_mocked_workflow_executes_exactly_once_without_keys_or_network(monkeypatch) -> None:
    for name in modal_app.readiness()["required_env_names"]:
        monkeypatch.delenv(name, raising=False)
    calls = []

    def executor(payload: dict) -> dict:
        calls.append(payload)
        return CASES["happy_path"]["output"]

    result = modal_app.execute_workflow(CASES["happy_path"]["input"], executor=executor)
    assert result == CASES["happy_path"]["output"]
    assert calls == [CASES["happy_path"]["input"]]


def test_live_executor_fails_closed_instead_of_returning_mock_artifacts() -> None:
    for name in modal_app.readiness()["required_env_names"]:
        os.environ.pop(name, None)
    with pytest.raises(modal_app.WorkflowNotReady):
        modal_app.execute_workflow(CASES["happy_path"]["input"])


def test_fastapi_surface_has_protected_async_submit_and_poll_routes() -> None:
    web = modal_app.create_fastapi_app()
    routes = {{(route.path, tuple(sorted(route.methods or []))) for route in web.routes}}
    assert ("/v1/runs", ("POST",)) in routes
    assert ("/v1/runs/{{call_id}}", ("GET",)) in routes


def test_default_submit_reports_not_ready_without_spawning() -> None:
    spawned = []
    web = modal_app.create_fastapi_app(spawn_runner=lambda payload: spawned.append(payload) or "fc")
    response = asyncio.run(_route(web, "/v1/runs").endpoint(CASES["happy_path"]["input"]))
    if EXPECTED_READY:
        assert response["status"] == "accepted"
        assert response["call_id"] == "fc"
        assert spawned == [CASES["happy_path"]["input"]]
    else:
        assert response.status_code == 503
        assert json.loads(response.body)["error"]["code"] == "WORKFLOW_NOT_READY"
        assert spawned == []


def test_injected_ready_contract_accepts_and_polls_completed_result() -> None:
    web = modal_app.create_fastapi_app(
        spawn_runner=lambda _payload: "fc-test",
        lookup_result=lambda _call_id: CASES["happy_path"]["output"],
        ready_override=True,
    )
    accepted = asyncio.run(_route(web, "/v1/runs").endpoint(CASES["happy_path"]["input"]))
    assert accepted["status"] == "accepted"
    assert accepted["call_id"] == "fc-test"
    completed = asyncio.run(_route(web, "/v1/runs/{{call_id}}").endpoint("fc-test"))
    assert completed == CASES["happy_path"]["output"]


def test_invalid_input_is_rejected_before_readiness_or_spawn() -> None:
    from fastapi import HTTPException

    spawned = []
    web = modal_app.create_fastapi_app(
        spawn_runner=lambda payload: spawned.append(payload) or "fc",
        ready_override=True,
    )
    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(_route(web, "/v1/runs").endpoint(CASES["negative_cases"][0]["input"]))
    assert exc_info.value.status_code == 422
    assert spawned == []


def test_manifest_and_capabilities_are_honest() -> None:
    manifest = json.loads((ROOT / "manifest.json").read_text(encoding="utf-8"))
    capabilities = json.loads((ROOT / "capability-manifest.json").read_text(encoding="utf-8"))
    assert manifest["readiness"]["can_submit"] is EXPECTED_READY
    assert manifest["pricing"]["chargeable"] is EXPECTED_CHARGEABLE
    assert capabilities["decision"] == ("approved" if EXPECTED_READY else "blocked")
    assert capabilities["approved"] == (capabilities["requested"] if EXPECTED_READY else [])
'''


def yaml_quote(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def container_yaml(profile: dict[str, Any], source_hash: str) -> str:
    blockers = profile["readiness"]["blockers"]
    steps = profile["steps"]
    ready = bool(profile["readiness"]["can_submit"])
    lines = [
        "spec_version: cognition.container/v1",
        f"name: {yaml_quote(profile['name'])}",
        f"slug: {profile['slug']}",
        f"version: {yaml_quote(profile['version'])}",
        f"status: {'ready' if ready else 'not-ready'}",
        "generated:",
        f"  compiler: {COMPILER_VERSION}",
        "  hand_edit_allowed: false",
        "source:",
        "  kind: vendored-skill-md",
        "  path: source/SKILL.md",
        f"  sha256: {source_hash}",
        "image:",
        "  base: debian-slim",
        '  python: "3.12"',
        "  packages:",
        "    - modal==1.5.0",
        "    - fastapi==0.109.0",
        "    - jsonschema==4.26.0",
    ]
    if profile.get("apt_packages"):
        lines.append("  apt_packages:")
        lines.extend(f"    - {item}" for item in profile["apt_packages"])
    lines.extend(
        [
            "resources:",
            f"  cpu: {profile['resources']['cpu']}",
            f"  memory_mb: {profile['resources']['memory_mb']}",
            f"  timeout_seconds: {runtime_timeout_seconds(profile)}",
            "  min_containers: 0",
            f"  max_containers: {profile['resources']['max_containers']}",
            "endpoint:",
            "  mode: async_job",
            "  submit_path: /v1/runs",
            "  result_path: /v1/runs/{call_id}",
            "  auth: modal_proxy_token",
            "  invalid_input_status: 422",
            "  not_ready_status: 503",
            "readiness:",
            f"  can_submit: {'true' if ready else 'false'}",
            f"  execution_kind: {profile['execution_kind']}",
            "  blockers:" if blockers else "  blockers: []",
        ]
    )
    for blocker in blockers:
        lines.extend(
            [
                f"    - code: {blocker['code']}",
                f"      detail: {yaml_quote(blocker['detail'])}",
            ]
        )
    lines.append("required_env_names:")
    lines.extend(f"  - {name}" for name in profile["required_env_names"])
    lines.append("steps:")
    for step in steps:
        lines.extend(
            [
                f"  - id: {step['id']}",
                f"    type: {step['type']}",
                f"    operation: {yaml_quote(step['operation'])}",
                f"    readiness: {step['readiness']}",
            ]
        )
        if step.get("provider"):
            lines.append(f"    provider: {step['provider']}")
        if step.get("prompt"):
            lines.append(f"    system_prompt: prompts/{step['prompt']}")
    lines.extend(
        [
            "input_schema: schemas/input.json",
            "output_schema: schemas/output.json",
            "frontend_manifest: manifest.json",
            "pricing_report: pricing-report.json",
            "tests:",
            "  contract: tests/test_contract.py",
            "  cases: tests/cases.json",
            "  network_allowed: false",
        ]
    )
    return "\n".join(lines) + "\n"


def readme(profile: dict[str, Any], source_hash: str, pricing: dict[str, Any]) -> str:
    blockers = "\n".join(
        f"- `{item['code']}` — {item['detail']}" for item in profile["readiness"]["blockers"]
    )
    env_names = "\n".join(f"- `{name}`" for name in profile["required_env_names"])
    prompts = "\n".join(f"- `prompts/{name}`" for name in sorted(profile["prompts"]))
    ready = bool(profile["readiness"]["can_submit"])
    readiness_copy = (
        "**READY for authenticated staging runs.** `POST /v1/runs` validates the input "
        "schema before spawning a provider-backed job."
        if ready else
        "**NOT READY for live runs or charging.** `POST /v1/runs` is protected with "
        "Modal Proxy Token auth and returns `503 WORKFLOW_NOT_READY` before spawning or "
        "spending while these blockers remain:"
    )
    blocker_copy = blockers if blockers else "- None for this reviewed runtime scope."
    price_copy = (
        f"`${pricing['display_price_usd']:.2f}` per run"
        if pricing["chargeable"] else
        f"display estimate `${pricing['display_price_usd']:.2f}`, not chargeable"
    )
    deploy_copy = (
        "Deploy after the named Modal secret exists and the offline tests pass:"
        if ready else
        "Deployment is intentionally gated on readiness review. Once the generated "
        "manifest says `can_submit: true`, required provider capabilities exist, and "
        "tests pass:"
    )
    return f"""# {profile['name']}

Generated Modal candidate for `{profile['slug']}`. The source skill is vendored
at `source/SKILL.md` (SHA-256 `{source_hash}`). Generated files must be changed
through the compiler profile, not edited by hand.

## Readiness

{readiness_copy}

{blocker_copy}

Required environment variable names (values never belong in this repository):

{env_names}

## Contract

- Submit: `POST /v1/runs` → `202` with `run_id`, `call_id`, and `result_url`
- Poll: `GET /v1/runs/{{call_id}}` → `202 running` or the validated output
- Invalid input: `422` before spawn
- Blocked release: `503` before spawn when `readiness.can_submit` is false
- Input/UI contract: `manifest.json`
- Pricing evidence: `pricing-report.json` ({price_copy})

Prompt assets:

{prompts}

## Rebuild and test

```bash
python3 packages/skill-to-modal/compiler.py \\
  containers/{profile['slug']}/source/SKILL.md \\
  --profile packages/skill-to-modal/profiles/{profile['slug']}.json \\
  --out containers/{profile['slug']}
python3 -m pytest -q -p no:cacheprovider containers/{profile['slug']}/tests/test_contract.py
```

{deploy_copy}

```bash
modal deploy containers/{profile['slug']}/modal_app.py
```
"""


def build_files(skill_text: str, profile: dict[str, Any]) -> dict[str, str]:
    parsed = parse_skill(skill_text)
    if profile.get("slug") != parsed["slug"]:
        raise ValueError(
            f"profile slug {profile.get('slug')!r} does not match skill {parsed['slug']!r}"
        )
    if profile.get("name") != parsed["name"]:
        raise ValueError("profile name does not match SKILL.md frontmatter")
    execution_kind = profile.get("execution_kind")
    readiness = profile["readiness"]
    ready = bool(readiness.get("can_submit"))
    if execution_kind not in ALLOWED_EXECUTION_KINDS and not readiness["blockers"]:
        raise ValueError("non-allowlisted execution kind must have blockers")
    if ready and execution_kind not in ALLOWED_EXECUTION_KINDS:
        raise ValueError("only allowlisted execution kinds may be ready")
    if ready and (readiness["blockers"] or not profile.get("live")):
        raise ValueError("ready single_llm profiles require live config and no blockers")

    source_hash = sha256_text(skill_text)
    pricing = price_report(profile)
    analysis = {
        "schema_version": "cognition.skill-analysis/v1",
        "compiler": COMPILER_VERSION,
        "name": parsed["name"],
        "slug": parsed["slug"],
        "description": parsed["description"],
        "source": {"path": "source/SKILL.md", "sha256": source_hash},
        "parsed_workflow_steps": parsed["extracted_steps"],
        "detected_provider_needs": parsed["detected_provider_needs"],
        "reviewed_steps": profile["steps"],
        "required_env_names": profile["required_env_names"],
        "cost_drivers": profile["cost_drivers"],
        "unresolved": profile["readiness"]["blockers"],
    }
    capabilities = {
        "schema_version": "cognition.capabilities/v1",
        "slug": profile["slug"],
        "execution_kind": execution_kind,
        "allowlist": sorted(ALLOWED_EXECUTION_KINDS),
        "requested": profile["capabilities"],
        "approved": profile["capabilities"] if ready else [],
        "decision": "approved" if ready else "blocked",
        "blockers": readiness["blockers"],
    }
    manifest = {
        "schema_version": "cognition.workflow-manifest/v1",
        "slug": profile["slug"],
        "name": profile["name"],
        "description": parsed["description"],
        "source_sha256": source_hash,
        "version": profile["version"],
        "readiness": {
            "status": "ready" if ready else "not_ready",
            "can_submit": ready,
            "blockers": readiness["blockers"],
            "required_env_names": profile["required_env_names"],
        },
        "endpoint": {
            "method": "POST",
            "path": "/v1/runs",
            "poll_path_template": "/v1/runs/{call_id}",
            "auth": "modal_proxy_token",
        },
        "input_schema": profile["input_schema"],
        "output_schema_path": "schemas/output.json",
        "form": profile["form"],
        "artifacts": profile["artifacts"],
        "pricing": {
            "currency": "USD",
            "display_price_usd": pricing["display_price_usd"],
            "label": (
                f"${pricing['display_price_usd']:.2f} per run"
                if ready and pricing["chargeable"]
                else f"Projected ${pricing['display_price_usd']:.2f} — unavailable"
            ),
            "chargeable": bool(pricing["chargeable"]) if ready else False,
            "quote_status": pricing["quote_status"],
            "report_path": "pricing-report.json",
        },
    }
    cases = {
        "happy_path": profile["happy_path"],
        "negative_cases": profile["negative_cases"],
    }
    files = {
        "README.md": readme(profile, source_hash, pricing),
        "container.yaml": container_yaml(profile, source_hash),
        "modal_app.py": modal_app_template(profile),
        "manifest.json": canonical_json(manifest),
        "pricing-report.json": canonical_json(pricing),
        "skill-analysis.json": canonical_json(analysis),
        "capability-manifest.json": canonical_json(capabilities),
        "schemas/input.json": canonical_json(profile["input_schema"]),
        "schemas/output.json": canonical_json(runtime_output_schema(profile)),
        "tests/cases.json": canonical_json(cases),
        "tests/test_contract.py": contract_test_template(profile),
        "source/SKILL.md": skill_text,
    }
    for name, prompt in profile["prompts"].items():
        files[f"prompts/{name}"] = prompt.strip() + "\n"
    return files


def write_or_check(files: dict[str, str], out: Path, check: bool) -> int:
    drift: list[str] = []
    for relative, content in sorted(files.items()):
        target = out / relative
        if check:
            if not target.is_file() or target.read_text(encoding="utf-8") != content:
                drift.append(relative)
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
    if drift:
        print("generated bundle drift: " + ", ".join(drift), file=sys.stderr)
        return 1
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("skill", type=Path)
    parser.add_argument("--profile", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    skill_text = args.skill.read_text(encoding="utf-8")
    profile = json.loads(args.profile.read_text(encoding="utf-8"))
    files = build_files(skill_text, profile)
    return write_or_check(files, args.out, args.check)


if __name__ == "__main__":
    raise SystemExit(main())
