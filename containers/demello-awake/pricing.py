"""Measured-cost evidence and guarded pricing for de Mello Awake.

The Modal app reports pricing evidence only.  The public gateway remains the
authority that quotes, reserves, debits, settles, or refunds buyer balances.
Unknown usage fields and non-finite/negative values fail closed so a newly
introduced provider unit cannot silently inherit an optimistic price.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from typing import Any


TARGET_MARGIN = 0.80
TAIL_RESERVE = 0.15
MINIMUM_PRICE_USD = 0.10

# Physical rates recorded by the Round-5 plan. Provider values are supplied as
# measured USD by the adapters because their units and prices are provider-
# specific and must not be guessed here.
MODAL_CPU_CORE_SECOND_USD = 0.0000131
MODAL_MEMORY_GIB_SECOND_USD = 0.00000222

PROVIDER_COMPONENTS = frozenset(
    {"transcription", "director", "image_generation"}
)
TOP_LEVEL_USAGE_FIELDS = frozenset(
    {
        "provider_costs_usd",
        "modal_cpu_core_seconds",
        "modal_memory_gib_seconds",
        "artifact_storage_usd",
        "artifact_egress_usd",
    }
)
HISTORY_FIELDS = frozenset(
    {
        "static_estimate_usd",
        "successful_delivered_usd",
        "delivered_7d_usd",
        "delivered_30d_usd",
    }
)


class PricingError(ValueError):
    """Raised when cost evidence is incomplete, ambiguous, or unsafe."""


def _money(value: Any, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise PricingError(f"{field} must be a numeric USD value")
    number = float(value)
    if not math.isfinite(number) or number < 0:
        raise PricingError(f"{field} must be finite and non-negative")
    return number


def _reject_unknown(mapping: Mapping[str, Any], allowed: frozenset[str], name: str) -> None:
    unknown = sorted(set(mapping) - allowed)
    if unknown:
        raise PricingError(f"unknown {name}: {', '.join(unknown)}")


def measured_usage_usd(usage: Mapping[str, Any]) -> float:
    """Convert one run's physical/provider usage into measured delivered USD."""

    if not isinstance(usage, Mapping):
        raise PricingError("usage must be an object")
    _reject_unknown(usage, TOP_LEVEL_USAGE_FIELDS, "usage fields")

    provider = usage.get("provider_costs_usd", {})
    if not isinstance(provider, Mapping):
        raise PricingError("provider_costs_usd must be an object")
    _reject_unknown(provider, PROVIDER_COMPONENTS, "provider cost components")

    total = sum(
        _money(value, f"provider_costs_usd.{name}")
        for name, value in provider.items()
    )
    total += _money(
        usage.get("modal_cpu_core_seconds", 0), "modal_cpu_core_seconds"
    ) * MODAL_CPU_CORE_SECOND_USD
    total += _money(
        usage.get("modal_memory_gib_seconds", 0),
        "modal_memory_gib_seconds",
    ) * MODAL_MEMORY_GIB_SECOND_USD
    total += _money(usage.get("artifact_storage_usd", 0), "artifact_storage_usd")
    total += _money(usage.get("artifact_egress_usd", 0), "artifact_egress_usd")
    return total


def provisional_success_p95(samples: Sequence[Any]) -> float:
    """Return a conservative provisional p95 from successful delivered runs.

    Fewer than 20 observations use the maximum, as required by the deployment
    plan. At 20+ observations this uses the nearest-rank p95.
    """

    if isinstance(samples, (str, bytes)) or not isinstance(samples, Sequence):
        raise PricingError("successful_delivered_usd must be an array")
    values = sorted(
        _money(value, f"successful_delivered_usd[{index}]")
        for index, value in enumerate(samples)
    )
    if not values:
        return 0.0
    if len(values) < 20:
        return values[-1]
    rank = max(1, math.ceil(0.95 * len(values)))
    return values[rank - 1]


def ceil_usd_cent(value: Any) -> float:
    """Round upward to a USD cent without binary-float under-rounding."""

    amount = _money(value, "price")
    return math.ceil((amount * 100) - 1e-12) / 100


def guarded_price_evidence(
    usage: Mapping[str, Any], history: Mapping[str, Any]
) -> dict[str, Any]:
    """Implement Round-5 C_guard and the 80%-margin upward-cent quote basis."""

    if not isinstance(history, Mapping):
        raise PricingError("history must be an object")
    _reject_unknown(history, HISTORY_FIELDS, "history fields")
    if "static_estimate_usd" not in history:
        raise PricingError("static_estimate_usd is required")

    measured = measured_usage_usd(usage)
    samples_raw = history.get("successful_delivered_usd", [])
    if not isinstance(samples_raw, Sequence) or isinstance(samples_raw, (str, bytes)):
        raise PricingError("successful_delivered_usd must be an array")
    samples = list(samples_raw)
    # The just-completed measured run is successful delivered evidence even if
    # the caller's history snapshot has not incorporated it yet.
    p95 = provisional_success_p95([*samples, measured])
    static = _money(history["static_estimate_usd"], "static_estimate_usd")
    delivered_7d = _money(history.get("delivered_7d_usd", 0), "delivered_7d_usd")
    delivered_30d = _money(
        history.get("delivered_30d_usd", 0), "delivered_30d_usd"
    )
    delivered_tail = max(delivered_7d, delivered_30d) * (1 + TAIL_RESERVE)
    guard = max(static, p95, delivered_tail)
    unrounded = max(MINIMUM_PRICE_USD, guard / (1 - TARGET_MARGIN))
    price = ceil_usd_cent(unrounded)

    return {
        "measured_usd": round(measured, 8),
        "success_p95_usd": round(p95, 8),
        "delivered_tail_usd": round(delivered_tail, 8),
        "guard_cost_usd": round(guard, 8),
        "guarded_price_usd": price,
        "target_margin": TARGET_MARGIN,
        "tail_reserve": TAIL_RESERVE,
        "successful_sample_size": len(samples) + 1,
    }

