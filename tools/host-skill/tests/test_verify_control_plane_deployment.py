"""Tests for exact Worker deploy receipt and live attestation."""
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
MODULE = ROOT / "tools" / "host-skill" / "verify_control_plane_deployment.py"
VERSION_ID = "8c0b7456-eeac-45e8-b65e-c0c7fcdccfd3"
SHA = "6beb3e5e4f4a01599861358646d16821aef5fcd4"
SELECTOR = "3a92372abf910f1ea26ba21d488a9ab5e6fc2b36"


def load_module():
    spec = importlib.util.spec_from_file_location("verify_control_plane_deployment", MODULE)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def valid_values():
    deploy_log = f"Uploaded cognition-demos\nCurrent Version ID: {VERSION_ID}\n"
    status = {"id": "dep_123", "versions": [{"version_id": VERSION_ID, "percentage": 100}]}
    version = {
        "id": VERSION_ID,
        "annotations": {"workers/message": f"omo-control-plane:{SHA}"},
        "resources": {"bindings": [
            {"name": "OMO_BUILDER_BASE_REVISION", "type": "plain_text", "text": SELECTOR},
            {"name": "SOME_SECRET", "type": "secret_text"},
        ]},
    }
    return deploy_log, status, version


def verify(deploy_log, status, version):
    module = load_module()
    return module.verify_deployment(
        deploy_log=deploy_log,
        deployment=status,
        version=version,
        expected_sha=SHA,
        expected_selector=SELECTOR,
    )


def test_exact_deploy_receipt_allocation_and_binding_pass() -> None:
    deploy_log, status, version = valid_values()
    assert verify(deploy_log, status, version) == {
        "allocation": 100,
        "selector": "verified",
        "version_id": VERSION_ID,
    }


@pytest.mark.parametrize("mutation", [
    "duplicate_receipt", "nested_allocation", "wrong_active_version", "split_allocation",
    "nested_binding", "wrong_binding_type", "wrong_annotation", "wrong_version_id",
])
def test_lookalike_or_unbound_evidence_fails_closed(mutation: str) -> None:
    deploy_log, status, version = valid_values()
    if mutation == "duplicate_receipt":
        deploy_log += f"Current Version ID: {VERSION_ID}\n"
    elif mutation == "nested_allocation":
        status = {"versions": [], "nested": {"version_id": VERSION_ID, "percentage": 100}}
    elif mutation == "wrong_active_version":
        status["versions"][0]["version_id"] = "11111111-1111-4111-8111-111111111111"
    elif mutation == "split_allocation":
        status["versions"] = [
            {"version_id": VERSION_ID, "percentage": 90},
            {"version_id": "11111111-1111-4111-8111-111111111111", "percentage": 10},
        ]
    elif mutation == "nested_binding":
        version["resources"]["bindings"] = []
        version["nested"] = {"name": "OMO_BUILDER_BASE_REVISION", "type": "plain_text", "text": SELECTOR}
    elif mutation == "wrong_binding_type":
        version["resources"]["bindings"][0]["type"] = "secret_text"
    elif mutation == "wrong_annotation":
        version["annotations"]["workers/message"] = f"unrelated:{SHA}"
    elif mutation == "wrong_version_id":
        version["id"] = "11111111-1111-4111-8111-111111111111"
    with pytest.raises(ValueError):
        verify(deploy_log, status, version)
