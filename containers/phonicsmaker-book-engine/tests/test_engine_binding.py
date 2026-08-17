import importlib.util
import sys
import types
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
MODULE_PATH = ROOT / "containers/phonicsmaker-book-engine/engine_binding.py"
spec = importlib.util.spec_from_file_location("phonicsmaker_engine_binding", MODULE_PATH)
assert spec is not None and spec.loader is not None
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)


def test_build_source_kwargs_preserves_full_payload_and_source_defaults():
    payload = {
        "phonemes": ["sh"],
        "story_idea": "A shell shines.",
        "difficulty_level": "2",
        "language_variant": "en_au",
        "include_activities": True,
        "activity_config": {"include_word_hunt": True},
        "include_audio": True,
        "focus_phonemes": ["sh"],
        "page_count": 7,
    }

    kwargs = module.build_source_kwargs(payload, task_id="task-1")

    assert kwargs["task_id"] == "task-1"
    assert kwargs["phonemes"] == ["sh"]
    assert kwargs["story_idea"] == "A shell shines."
    assert kwargs["difficulty_level"] == "2"
    assert kwargs["language_variant"] == "en_au"
    assert kwargs["include_activities"] is True
    assert kwargs["activity_config"] == {"include_word_hunt": True}
    assert kwargs["focus_phonemes"] == ["sh"]
    assert kwargs["page_count"] == 7
    assert kwargs["user_email"] is None
    assert kwargs["is_free"] is False
    assert kwargs["job"] is None


def test_artifact_store_hashes_and_records_private_upload(tmp_path):
    source = tmp_path / "book.pdf"
    source.write_bytes(b"pdf-fixture")
    store = module.LocalArtifactStore(tmp_path / "artifacts", public_base_url="https://omo.invalid/artifacts")

    url = __import__("asyncio").run(store.upload_result(str(source), "task-1"))

    assert url == "https://omo.invalid/artifacts/task-1/book.pdf"
    assert (tmp_path / "artifacts/task-1/book.pdf").read_bytes() == b"pdf-fixture"
    assert store.records[0].sha256 == "96843789fe654015c210e658d842d50d2736194c75a81ba3a95eb4e4f8489c5a"


def test_boundary_restores_source_module_dependencies(tmp_path):
    original_upload = object()
    original_callback = object()
    source_module = types.SimpleNamespace(upload_result=original_upload, callback_service=original_callback)
    store = module.LocalArtifactStore(tmp_path / "artifacts")
    callback = module.OmoCallback()

    with module.SourceRuntimeBoundary(source_module, store, callback):
        assert source_module.upload_result == store.upload_result
        assert source_module.callback_service is callback

    assert source_module.upload_result is original_upload
    assert source_module.callback_service is original_callback


def test_source_binding_normalizes_all_uploaded_source_artifacts(tmp_path):
    store = module.LocalArtifactStore(tmp_path / "artifacts", public_base_url="https://omo.invalid/artifacts")
    urls = {}
    for name in ("pdf", "pdf_compressed", "thumbnail", "book_only", "worksheets", "homework", "answer_key", "pptx", "draft"):
        path = tmp_path / f"{name}.bin"
        path.write_bytes(name.encode())
        urls[name] = __import__("asyncio").run(store.upload_result(str(path), "task-1"))

    source_result = {
        "task_id": "task-1",
        "pdf_url": urls["pdf"],
        "pdf_compressed_url": urls["pdf_compressed"],
        "thumbnail_url": urls["thumbnail"],
        "book_only_url": urls["book_only"],
        "worksheets_url": urls["worksheets"],
        "homework_url": urls["homework"],
        "answer_key_url": urls["answer_key"],
        "pptx_url": urls["pptx"],
        "draft_data": {"pages": []},
        "variations": {},
        "scenes": [],
        "phonemes": ["sh"],
        "audio_manifest": None,
    }

    normalized = module.normalize_source_result(source_result, store, run_id="run-12345678")

    assert normalized["status"] == "completed"
    assert normalized["pdf_url"] == urls["pdf"]
    assert normalized["pptx_url"] == urls["pptx"]
    assert normalized["draft_data"] == {"pages": []}
    assert {artifact["role"] for artifact in normalized["artifacts"]} == {
        "book_pdf", "book_compressed_pdf", "thumbnail", "book_only_pdf",
        "worksheets_pdf", "homework_pdf", "answer_key_pdf", "pptx", "editable_source",
    }


def test_source_binding_patches_boundary_and_returns_normalized_result(tmp_path):
    source_module = types.SimpleNamespace()
    source_module.upload_result = None
    source_module.callback_service = None
    store = module.LocalArtifactStore(tmp_path / "artifacts", public_base_url="https://omo.invalid/artifacts")

    async def fake_source_task(**kwargs):
        path = tmp_path / "book.pdf"
        path.write_bytes(b"book")
        url = await source_module.upload_result(str(path), kwargs["task_id"])
        return {
            "task_id": kwargs["task_id"],
            "pdf_url": url,
            "pdf_compressed_url": None,
            "thumbnail_url": None,
            "book_only_url": None,
            "worksheets_url": None,
            "homework_url": None,
            "answer_key_url": None,
            "pptx_url": None,
            "variations": {},
            "scenes": [],
            "phonemes": kwargs["phonemes"],
            "audio_manifest": None,
            "draft_data": None,
        }

    binding = module.SourceEngineBinding(
        source_module=source_module,
        source_task=fake_source_task,
        artifact_store=store,
        service_factories=(lambda: object(), lambda: object(), lambda: object()),
    )
    result = __import__("asyncio").run(binding.run({"phonemes": ["sh"], "story_idea": "A shell.", "difficulty_level": "2"}, "task-1"))

    assert result["pdf_url"] == "https://omo.invalid/artifacts/task-1/book.pdf"
    assert result["artifacts"][0]["role"] == "book_pdf"
    assert source_module.upload_result is None
    assert source_module.callback_service is None
