from __future__ import annotations

import importlib.util
import math
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("demello_awake_pricing", ROOT / "pricing.py")
assert spec and spec.loader
pricing = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pricing)


def usage(**overrides):
    value = {
        "provider_costs_usd": {
            "transcription": 0.01,
            "director": 0.01,
            "image_generation": 0.08,
        },
        "provider_costs_complete": True,
        "modal_cpu_core_seconds": 10,
        "modal_memory_gib_seconds": 20,
        "artifact_storage_usd": 0.001,
        "artifact_egress_usd": 0.002,
    }
    value.update(overrides)
    return value


def test_measured_usage_includes_provider_modal_and_artifact_costs() -> None:
    measured = pricing.measured_usage_usd(usage())
    expected = 0.103 + 10 * pricing.MODAL_CPU_CORE_SECOND_USD + 20 * pricing.MODAL_MEMORY_GIB_SECOND_USD
    assert measured == pytest.approx(expected)


def test_round_five_guard_tail_margin_and_upward_cent() -> None:
    evidence = pricing.guarded_price_evidence(
        usage(provider_costs_usd={"image_generation": 0.01}),
        {
            "static_estimate_usd": 0.05,
            "successful_delivered_usd": [0.10, 0.11],
            "delivered_7d_usd": 0.12,
            "delivered_30d_usd": 0.10,
        },
    )
    assert evidence["delivered_tail_usd"] == pytest.approx(0.138)
    assert evidence["guard_cost_usd"] == pytest.approx(0.138)
    assert evidence["guarded_price_usd"] == 0.69
    assert evidence["target_margin"] == 0.80
    assert evidence["tail_reserve"] == 0.15


def test_price_floor_and_provisional_p95_max() -> None:
    evidence = pricing.guarded_price_evidence(
        {"provider_costs_usd": {}, "provider_costs_complete": True},
        {"static_estimate_usd": 0, "successful_delivered_usd": [0.001, 0.002]},
    )
    assert evidence["success_p95_usd"] == 0.002
    assert evidence["guarded_price_usd"] == 0.10


@pytest.mark.parametrize(
    "bad_usage",
    [
        {"unknown_unit": 1},
        {"provider_costs_usd": {"unreviewed_provider": 1}},
        {"modal_cpu_core_seconds": -1},
        {"artifact_egress_usd": math.inf},
    ],
)
def test_unknown_or_invalid_usage_fails_closed(bad_usage) -> None:
    with pytest.raises(pricing.PricingError):
        pricing.measured_usage_usd(bad_usage)


def test_incomplete_subscription_provider_cost_fails_closed() -> None:
    with pytest.raises(pricing.PricingError, match="incomplete"):
        pricing.guarded_price_evidence(
            usage(provider_costs_complete=False),
            {"static_estimate_usd": 0.25},
        )
