import json
import os
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import MagicMock

os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/test")

import pytest

from app.phonics_maker.task_management import task_service as task_service_module
from app.phonics_maker.task_management.task_service import TaskService

DRAFT_DATA_DIR = Path(task_service_module.__file__).resolve().parent.parent.parent.parent / "draft_data"


@pytest.fixture
def service():
    return TaskService()


def _mock_session_scope(monkeypatch, generation):
    session = MagicMock()
    session.query.return_value.filter.return_value.first.return_value = generation

    @contextmanager
    def fake_scope():
        yield session

    monkeypatch.setattr(task_service_module, "session_scope", fake_scope)


def _generation_with_metadata(task_metadata):
    generation = MagicMock()
    generation.task_metadata = task_metadata
    return generation


def test_resolves_from_dict_metadata(service, monkeypatch):
    _mock_session_scope(monkeypatch, _generation_with_metadata({
        "draft_data": {"character_description": "a red fox in a blue scarf", "book_seed": 12345}
    }))
    desc, seed = service.get_reference_book_fields("task-1", "owner@example.com")
    assert desc == "a red fox in a blue scarf"
    assert seed == 12345


def test_resolves_from_string_metadata(service, monkeypatch):
    metadata = json.dumps({
        "draft_data": {"character_description": "a green dragon", "book_seed": "777"}
    })
    _mock_session_scope(monkeypatch, _generation_with_metadata(metadata))
    desc, seed = service.get_reference_book_fields("task-2", "owner@example.com")
    assert desc == "a green dragon"
    assert seed == 777


def test_legacy_metadata_without_draft_data(service, monkeypatch):
    _mock_session_scope(monkeypatch, _generation_with_metadata({"phonemes": ["sh"]}))
    desc, seed = service.get_reference_book_fields("no-such-task-on-disk")
    assert desc is None
    assert seed is None


def test_missing_row_and_no_disk_file(service, monkeypatch):
    _mock_session_scope(monkeypatch, None)
    desc, seed = service.get_reference_book_fields("no-such-task-on-disk")
    assert desc is None
    assert seed is None


def test_non_numeric_seed_still_returns_description(service, monkeypatch):
    _mock_session_scope(monkeypatch, _generation_with_metadata({
        "draft_data": {"character_description": "a shy owl", "book_seed": "not-a-number"}
    }))
    desc, seed = service.get_reference_book_fields("task-3", "owner@example.com")
    assert desc == "a shy owl"
    assert seed is None


def test_without_owner_email_does_not_resolve_from_db(service, monkeypatch):
    # A reference book must only be resolvable by its owner; without an owner
    # email the DB row is never consulted, so no cross-user carryover leaks.
    _mock_session_scope(monkeypatch, _generation_with_metadata({
        "draft_data": {"character_description": "someone else's character", "book_seed": 999}
    }))
    desc, seed = service.get_reference_book_fields("task-owned-by-another-user")
    assert desc is None
    assert seed is None


def test_db_error_falls_back_to_disk(service, monkeypatch):
    @contextmanager
    def failing_scope():
        raise RuntimeError("db down")
        yield

    monkeypatch.setattr(task_service_module, "session_scope", failing_scope)

    task_id = "test-reference-disk-fallback"
    DRAFT_DATA_DIR.mkdir(exist_ok=True)
    filepath = DRAFT_DATA_DIR / f"{task_id}.json"
    filepath.write_text(json.dumps({
        "character_description": "a brave rabbit", "book_seed": 42
    }))
    try:
        desc, seed = service.get_reference_book_fields(task_id)
    finally:
        filepath.unlink()
    assert desc == "a brave rabbit"
    assert seed == 42


def test_legacy_disk_file_without_reference_fields(service, monkeypatch):
    _mock_session_scope(monkeypatch, None)

    task_id = "test-reference-legacy-disk"
    DRAFT_DATA_DIR.mkdir(exist_ok=True)
    filepath = DRAFT_DATA_DIR / f"{task_id}.json"
    filepath.write_text(json.dumps({"story_title": "Old Book", "scenes": []}))
    try:
        desc, seed = service.get_reference_book_fields(task_id)
    finally:
        filepath.unlink()
    assert desc is None
    assert seed is None
