import importlib.util
import json
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[3]
MODULE_PATH = ROOT / "containers/phonicsmaker-book-engine/book_adapter.py"
spec = importlib.util.spec_from_file_location("phonicsmaker_book_adapter", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)


def full_payload():
    return {
        "phonemes": ["sh", "ch"],
        "story_idea": "A chick finds a shiny shell by the farm shed.",
        "difficulty_level": "2",
        "language_variant": "en_au",
        "curriculum": "general",
        "year_level": "Year 1-2",
        "student_age": "6",
        "vocabulary_mode": "decodable",
        "focus_mode": "phonics",
        "known_phonemes": ["s", "h"],
        "focus_phonemes": ["sh", "ch"],
        "sight_words": ["a", "the"],
        "strict_decodable": True,
        "morphology_focus": ["-s"],
        "story_format": "storybook",
        "highlight_text": True,
        "illustration_style": "vivid_cartoon",
        "story_type": "narrative",
        "book_layout": "classic",
        "book_font": "lexie_readable",
        "page_count": 7,
        "include_activities": True,
        "activity_config": {"include_word_hunt": True, "include_tracing": True},
        "series_info": {"book_position": 1, "total_books": 3, "series_name": "Farm Friends"},
        "book_title": "The Shiny Shell",
        "series_characters": ["Chick", "Sam"],
        "series_theme": "farm adventures",
        "character_pronouns": "they/them",
        "reference_task_id": "owned-source-123",
        "reference_character_description": "A small yellow chick with a blue scarf.",
        "reference_seed": 42,
    }


def full_result():
    return {
        "run_id": "run-phonicsmaker-12345678",
        "status": "completed",
        "workflow_version": "phonicsmaker-core@source-4c31dc2",
        "task_id": "task-phonicsmaker-12345678",
        "pdf_url": "https://artifact.invalid/book.pdf",
        "pdf_compressed_url": "https://artifact.invalid/book-compressed.pdf",
        "thumbnail_url": "https://artifact.invalid/thumbnail.jpg",
        "book_only_url": "https://artifact.invalid/book-only.pdf",
        "worksheets_url": "https://artifact.invalid/worksheets.pdf",
        "homework_url": "https://artifact.invalid/homework.pdf",
        "answer_key_url": "https://artifact.invalid/answer-key.pdf",
        "pptx_url": "https://artifact.invalid/book.pptx",
        "variations": {"3": "https://artifact.invalid/variation-3.pdf"},
        "scenes": ["A chick finds a shell.", "The chick shares it."],
        "phonemes": ["sh", "ch"],
        "audio_manifest": None,
        "draft_data": {"story_title": "The Shiny Shell", "pages": []},
        "artifacts": [
            {"role": "book_pdf", "kind": "pdf", "filename": "book.pdf", "content_type": "application/pdf", "bytes": 10, "sha256": "a" * 64, "url": "https://artifact.invalid/book.pdf"},
            {"role": "book_compressed_pdf", "kind": "pdf", "filename": "book-compressed.pdf", "content_type": "application/pdf", "bytes": 10, "sha256": "b" * 64, "url": "https://artifact.invalid/book-compressed.pdf"},
            {"role": "thumbnail", "kind": "image", "filename": "thumbnail.jpg", "content_type": "image/jpeg", "bytes": 10, "sha256": "c" * 64, "url": "https://artifact.invalid/thumbnail.jpg"},
            {"role": "book_only_pdf", "kind": "pdf", "filename": "book-only.pdf", "content_type": "application/pdf", "bytes": 10, "sha256": "d" * 64, "url": "https://artifact.invalid/book-only.pdf"},
            {"role": "worksheets_pdf", "kind": "pdf", "filename": "worksheets.pdf", "content_type": "application/pdf", "bytes": 10, "sha256": "e" * 64, "url": "https://artifact.invalid/worksheets.pdf"},
            {"role": "homework_pdf", "kind": "pdf", "filename": "homework.pdf", "content_type": "application/pdf", "bytes": 10, "sha256": "f" * 64, "url": "https://artifact.invalid/homework.pdf"},
            {"role": "answer_key_pdf", "kind": "pdf", "filename": "answer-key.pdf", "content_type": "application/pdf", "bytes": 10, "sha256": "0" * 64, "url": "https://artifact.invalid/answer-key.pdf"},
            {"role": "pptx", "kind": "pptx", "filename": "book.pptx", "content_type": "application/vnd.openxmlformats-officedocument.presentationml.presentation", "bytes": 10, "sha256": "1" * 64, "url": "https://artifact.invalid/book.pptx"},
            {"role": "editable_source", "kind": "json", "filename": "draft.json", "content_type": "application/json", "bytes": 10, "sha256": "2" * 64, "url": "https://artifact.invalid/draft.json"},
        ],
        "usage": {"provider_calls": 0, "estimated_cost_usd": 0.0},
    }


def test_full_book_payload_is_forwarded_unchanged_and_full_result_is_returned():
    captured = {}

    def spawn(payload):
        captured.update(payload)
        return "call-123"

    app = module.create_book_app(spawn_runner=spawn, lookup_result=lambda call_id: full_result())
    client = TestClient(app)

    response = client.post("/v1/runs", json=full_payload())
    assert response.status_code == 202
    assert response.json()["status"] == "accepted"
    assert captured == full_payload()

    result = client.get("/v1/runs/call-123")
    assert result.status_code == 200
    body = result.json()
    assert body["pdf_url"] == "https://artifact.invalid/book.pdf"
    assert body["worksheets_url"] == "https://artifact.invalid/worksheets.pdf"
    assert body["book_only_url"] == "https://artifact.invalid/book-only.pdf"
    assert body["homework_url"] == "https://artifact.invalid/homework.pdf"
    assert body["answer_key_url"] == "https://artifact.invalid/answer-key.pdf"
    assert body["pptx_url"] == "https://artifact.invalid/book.pptx"
    assert len(body["artifacts"]) == 9


def test_missing_required_book_input_is_rejected_before_spawn():
    called = False

    def spawn(payload):
        nonlocal called
        called = True
        return "call-never"

    app = module.create_book_app(spawn_runner=spawn, lookup_result=lambda call_id: full_result())
    response = TestClient(app).post("/v1/runs", json={"phonemes": ["sh"]})

    assert response.status_code == 422
    assert not called


def test_unbound_engine_fails_closed_without_fake_success():
    app = module.create_book_app()
    response = TestClient(app).post("/v1/runs", json=full_payload())

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "PHONICSMAKER_ENGINE_NOT_BOUND"


def test_running_poll_returns_202():
    def lookup(call_id):
        raise TimeoutError

    app = module.create_book_app(spawn_runner=lambda payload: "call-running", lookup_result=lookup)
    response = TestClient(app).get("/v1/runs/call-running")

    assert response.status_code == 202
    assert response.json()["status"] == "running"
