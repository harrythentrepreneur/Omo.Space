"""Bind the preserved PhonicsMaker source task to Omo-owned boundaries."""

from __future__ import annotations

import asyncio
import hashlib
import importlib
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import Any, Callable
from urllib.parse import urlparse

SOURCE_ARTIFACT_FIELDS = {
    "pdf_url": ("book_pdf", "pdf"),
    "pdf_compressed_url": ("book_compressed_pdf", "pdf"),
    "thumbnail_url": ("thumbnail", "image"),
    "book_only_url": ("book_only_pdf", "pdf"),
    "worksheets_url": ("worksheets_pdf", "pdf"),
    "homework_url": ("homework_pdf", "pdf"),
    "answer_key_url": ("answer_key_pdf", "pdf"),
    "pptx_url": ("pptx", "pptx"),
}


@dataclass(frozen=True)
class ArtifactRecord:
    url: str
    task_id: str
    filename: str
    content_type: str
    kind: str
    bytes: int
    sha256: str


class LocalArtifactStore:
    """Offline artifact plane used by tests and local binding probes."""

    def __init__(self, root: Path, public_base_url: str = "https://omo.invalid/artifacts"):
        self.root = Path(root)
        self.public_base_url = public_base_url.rstrip("/")
        self.records: list[ArtifactRecord] = []

    async def upload_result(self, file_path: str, task_id: str) -> str:
        source = Path(file_path)
        if not source.is_file():
            raise FileNotFoundError(file_path)
        destination = self.root / task_id / source.name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        digest = hashlib.sha256(destination.read_bytes()).hexdigest()
        ext = source.suffix.lower()
        content_type = {
            ".pdf": "application/pdf",
            ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".json": "application/json",
            ".mp3": "audio/mpeg",
        }.get(ext, "application/octet-stream")
        url = f"{self.public_base_url}/{task_id}/{source.name}"
        record = ArtifactRecord(
            url=url,
            task_id=task_id,
            filename=source.name,
            content_type=content_type,
            kind={
                "application/pdf": "pdf",
                "application/vnd.openxmlformats-officedocument.presentationml.presentation": "pptx",
                "application/json": "json",
                "audio/mpeg": "audio",
            }.get(content_type, "image"),
            bytes=destination.stat().st_size,
            sha256=digest,
        )
        self.records.append(record)
        return url

    def find(self, url: str | None, *, filename_hint: str | None = None) -> ArtifactRecord | None:
        if url:
            for record in reversed(self.records):
                if record.url == url:
                    return record
            basename = Path(urlparse(url).path).name
            if basename:
                filename_hint = basename
        if filename_hint:
            for record in reversed(self.records):
                if record.filename == filename_hint:
                    return record
        return None


class OmoCallback:
    """Progress sink that never calls the PhonicsMaker web app."""

    def __init__(self):
        self.events: list[dict[str, Any]] = []

    async def send_progress(self, task_id: str, progress: int, message: str | None = None) -> bool:
        self.events.append({"type": "progress", "task_id": task_id, "progress": progress, "message": message})
        return True

    async def send_intermediate_data(self, task_id: str, data: dict[str, Any]) -> bool:
        self.events.append({"type": "intermediate", "task_id": task_id, "data": data})
        return True

    async def send_completion(self, *args: Any, **kwargs: Any) -> bool:
        self.events.append({"type": "completion"})
        return True

    async def send_draft_completion(self, *args: Any, **kwargs: Any) -> bool:
        self.events.append({"type": "draft_completion"})
        return True

    async def send_error(self, *args: Any, **kwargs: Any) -> bool:
        self.events.append({"type": "error"})
        return True


class OmoTaskService:
    """Task state boundary; Omo control-plane persistence is injected later."""

    def __init__(self):
        self.events: list[dict[str, Any]] = []

    def set_task_result(self, task_id: str, **kwargs: Any) -> None:
        self.events.append({"type": "result", "task_id": task_id, "kwargs": kwargs})

    def update_task_progress(self, task_id: str, progress: int, message: str | None = None) -> None:
        self.events.append({"type": "progress", "task_id": task_id, "progress": progress, "message": message})

    def set_user_email_for_task(self, task_id: str, user_email: str) -> None:
        raise RuntimeError("PhonicsMaker email identity is not accepted by the Omo engine boundary")

    def get_reference_book_fields(self, task_id: str, user_email: str | None = None) -> tuple[None, None]:
        raise RuntimeError("Reference-book ownership must be resolved by Omo before engine execution")


def build_source_kwargs(payload: dict[str, Any], task_id: str) -> dict[str, Any]:
    """Map the Omo teacher payload to the source task's full argument surface."""
    names = (
        "phonemes", "story_idea", "difficulty_level", "language_variant",
        "include_activities", "activity_config", "illustration_style", "story_type",
        "book_layout", "book_font", "known_phonemes", "focus_phonemes", "sight_words",
        "strict_decodable", "vocabulary_mode", "focus_mode", "morphology_focus",
        "story_format", "student_age", "year_level", "curriculum", "highlight_text",
        "series_info", "book_title", "series_characters", "series_theme",
        "character_pronouns", "page_count", "reference_character_description", "reference_seed",
    )
    kwargs = {name: payload.get(name) for name in names}
    kwargs.update({
        "task_id": task_id,
        "task_service": None,
        "story_service_instance": None,
        "image_service_instance": None,
        "is_free": False,
        "debug_config": None,
        "user_email": None,
        "job": None,
        "include_audio": False,
        "audio_config": None,
        "target_difficulties": None,
        "draft_only": False,
        "standard_codes": None,
    })
    return kwargs


class SourceRuntimeBoundary:
    def __init__(self, source_module: ModuleType | Any, artifact_store: LocalArtifactStore, callback: OmoCallback):
        self.source_module = source_module
        self.artifact_store = artifact_store
        self.callback = callback
        self.original_upload = None
        self.original_callback = None

    def __enter__(self):
        self.original_upload = getattr(self.source_module, "upload_result", None)
        self.original_callback = getattr(self.source_module, "callback_service", None)
        self.source_module.upload_result = self.artifact_store.upload_result
        self.source_module.callback_service = self.callback
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.source_module.upload_result = self.original_upload
        self.source_module.callback_service = self.original_callback
        return False


def _artifact_from_record(record: ArtifactRecord, role: str, kind: str) -> dict[str, Any]:
    return {
        "role": role,
        "kind": kind,
        "filename": record.filename,
        "content_type": record.content_type,
        "bytes": record.bytes,
        "sha256": record.sha256,
        "url": record.url,
    }


def normalize_source_result(source_result: dict[str, Any], artifact_store: LocalArtifactStore, run_id: str) -> dict[str, Any]:
    normalized = dict(source_result)
    normalized["run_id"] = run_id
    normalized["status"] = "completed"
    normalized["workflow_version"] = "phonicsmaker-core@source-4c31dc2"
    artifacts: list[dict[str, Any]] = []
    for field, (role, kind) in SOURCE_ARTIFACT_FIELDS.items():
        value = source_result.get(field)
        if not value:
            continue
        record = artifact_store.find(value)
        if record is None:
            raise RuntimeError(f"source artifact was not captured by Omo store: {field}")
        normalized[field] = record.url
        artifacts.append(_artifact_from_record(record, role, kind))

    variations = source_result.get("variations") or {}
    if isinstance(variations, dict):
        for label, value in variations.items():
            record = artifact_store.find(value)
            if record is not None:
                normalized["variations"][label] = record.url
                artifacts.append(_artifact_from_record(record, f"variation_{label}", "pdf"))

    if source_result.get("draft_data") is not None:
        draft_record = artifact_store.find(None, filename_hint="draft.json")
        if draft_record is None:
            draft_record = next((record for record in reversed(artifact_store.records) if "draft" in record.filename), None)
        if draft_record is not None:
            artifacts.append(_artifact_from_record(draft_record, "editable_source", "json"))

    if not artifacts:
        raise RuntimeError("source engine returned no captured artifacts")
    normalized["artifacts"] = artifacts
    normalized["usage"] = normalized.get("usage") or {"source_engine": "phonicsmaker-core", "provider_calls": None}
    return normalized


class SourceEngineBinding:
    def __init__(self, source_module: ModuleType | Any, source_task: Callable[..., Any], artifact_store: LocalArtifactStore, service_factories: tuple[Callable[[], Any], Callable[[], Any], Callable[[], Any]]):
        self.source_module = source_module
        self.source_task = source_task
        self.artifact_store = artifact_store
        self.service_factories = service_factories

    async def run(self, payload: dict[str, Any], task_id: str) -> dict[str, Any]:
        task_service = self.service_factories[0]()
        story_service = self.service_factories[1]()
        image_service = self.service_factories[2]()
        kwargs = build_source_kwargs(payload, task_id)
        kwargs.update({
            "task_service": task_service,
            "story_service_instance": story_service,
            "image_service_instance": image_service,
        })
        callback = OmoCallback()
        existing_tasks = set(asyncio.all_tasks())
        with SourceRuntimeBoundary(self.source_module, self.artifact_store, callback):
            source_result = await self.source_task(**kwargs)
            new_tasks = [task for task in asyncio.all_tasks() if task not in existing_tasks and task is not asyncio.current_task()]
            if new_tasks:
                await asyncio.gather(*new_tasks, return_exceptions=False)
        return normalize_source_result(source_result, self.artifact_store, run_id=f"run-{task_id}")


def load_source_binding(source_root: Path, artifact_store: LocalArtifactStore) -> SourceEngineBinding:
    source_root = Path(source_root).resolve()
    sys.path.insert(0, str(source_root))
    module = importlib.import_module("app.phonics_maker.tasks.story_tasks")
    from app.phonics_maker.image_generation.image_service import ImageService
    from app.phonics_maker.story_generation.story_service import StoryService

    return SourceEngineBinding(
        source_module=module,
        source_task=module.generate_story_task,
        artifact_store=artifact_store,
        service_factories=(OmoTaskService, StoryService, ImageService),
    )
