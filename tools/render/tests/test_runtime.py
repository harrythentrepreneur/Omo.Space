from __future__ import annotations

import base64
import io
import json
from pathlib import Path

import pytest
from PIL import Image
from pypdf import PdfReader

from tools.render.image_bridge import codex_subscription_adapter
from tools.render.runtime import (
    ArtifactAccessError,
    ArtifactStore,
    ManifestError,
    apply_edit_operations,
    render_manifest,
)


def worksheet_manifest() -> dict:
    return {
        "schema_version": "omo.education-artifact-manifest/v1",
        "workflow_slug": "phonics-worksheet-generator",
        "document_id": "worksheet-1",
        "title": "The ch Check",
        "filename_stem": "ch-check",
        "include_answer_key": True,
        "pages": [{
            "page_number": 1,
            "heading": "Choose the ch word",
            "body": ["Circle the target word."],
            "items": [{"id": "one", "prompt": "chip or sip", "answer": "chip"}],
        }],
    }


def story_manifest(slug: str = "illustrated-decodable-story-maker") -> dict:
    return {
        "schema_version": "omo.education-artifact-manifest/v1",
        "workflow_slug": slug,
        "document_id": "story-1",
        "title": "Chip and the Chick",
        "filename_stem": "chip-and-the-chick",
        "phonemes": ["ch"],
        "highlight_text": True,
        "pages": [{
            "page_number": 1,
            "heading": "At the Shop",
            "body": ["Chip met a chick at the shop."],
            "items": [],
            "image_prompt": "A child and a yellow chick outside a small shop.",
        }],
    }


def test_worksheet_and_answer_key_are_real_pdfs(tmp_path: Path) -> None:
    result = render_manifest(worksheet_manifest(), tmp_path)
    assert [item.role for item in result.artifacts] == ["worksheet", "answer_key"]
    for artifact in result.artifacts:
        path = Path(artifact.object_key)
        assert path.stat().st_size == artifact.bytes
        assert len(PdfReader(str(path)).pages) == 1


def test_story_text_only_produces_all_declared_local_artifacts(tmp_path: Path) -> None:
    result = render_manifest(story_manifest(), tmp_path)
    assert [item.kind for item in result.artifacts] == ["pdf", "json", "thumbnail"]
    assert result.warnings == ("text-only fallback: no authorized/generated image supplied for page(s) 1",)
    assert len(PdfReader(str(tmp_path / "chip-and-the-chick.pdf")).pages) == 1
    assert json.loads((tmp_path / "chip-and-the-chick.json").read_text())["title"] == "Chip and the Chick"


def test_store_is_owner_scoped_and_immutable(tmp_path: Path) -> None:
    store = ArtifactStore(tmp_path / "store", "owner-a")
    result = render_manifest(worksheet_manifest(), tmp_path / "out", store=store, run_id="run-1")
    descriptor = result.artifacts[0].to_dict()
    assert store.read_owned(descriptor).startswith(b"%PDF-")
    foreign = dict(descriptor, object_key=descriptor["object_key"].replace("owner-a/", "owner-b/", 1))
    with pytest.raises(ArtifactAccessError):
        store.read_owned(foreign)


def test_edit_operations_copy_source_and_reject_image_tier() -> None:
    source = story_manifest("phonics-story-edit-studio")
    edited = apply_edit_operations(source, [
        {"operation": "change_story_title", "new_title": "A New Title"},
        {"operation": "change_scene_text", "page_number": 1, "text": "A changed scene."},
    ])
    assert edited["title"] == "A New Title"
    assert edited["pages"][0]["body"] == ["A changed scene."]
    assert source["title"] == "Chip and the Chick"
    with pytest.raises(ManifestError, match="reviewed image tier"):
        apply_edit_operations(source, [{"operation": "regenerate_scene_image"}])


def test_missing_answer_fails_before_writing_key(tmp_path: Path) -> None:
    manifest = worksheet_manifest()
    del manifest["pages"][0]["items"][0]["answer"]
    with pytest.raises(ManifestError, match="answers are missing"):
        render_manifest(manifest, tmp_path)


def test_codex_adapter_bridge_is_offline_injectable_and_disables_refresh(monkeypatch) -> None:
    monkeypatch.setenv("OPENAI_CODEX_REFRESH_TOKEN", "ignored-offline-test-refresh-token")
    buffer = io.BytesIO()
    Image.new("RGB", (32, 32), "white").save(buffer, "PNG")
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")

    def fake_request(**kwargs):
        assert kwargs["prompt"] == "test prompt"
        return {"data": [{"b64_json": encoded}]}

    adapter = codex_subscription_adapter(
        access_token="offline-test-token",
        account_id="offline-test-account",
        request=fake_request,
    )
    image, usage = adapter.generate("test prompt")
    assert image == buffer.getvalue()
    assert usage == {}
    assert adapter.allow_refresh is False
    assert adapter.refresh_token is None
