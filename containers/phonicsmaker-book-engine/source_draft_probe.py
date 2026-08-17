import asyncio
import sys
from pathlib import Path

sys.path.insert(0, "/opt/phonicsmaker")
sys.path.insert(0, "/opt/omo")

from app.db.models.image import SceneImage
from app.phonics_maker.tasks import story_tasks
from engine_binding import LocalArtifactStore, OmoCallback, OmoTaskService, SourceRuntimeBoundary


class OfflineStoryService:
    async def generate_short_scenes(self, *args, **kwargs):
        return "The Shiny Shell", ["A chick finds a shell.", "The chick shares it."]

    async def generate_scene_image_prompts(self, *args, **kwargs):
        return ["A chick beside a shell.", "Two friends share a shell."]


class OfflineImageService:
    COVER_NEGATIVE_PROMPT = "no text"

    def __init__(self):
        self.use_ace_plus_plus = False
        self._book_seed = 123

    async def generate_cover_visual_description(self, *args, **kwargs):
        return "A small yellow chick with a blue scarf stands beside a shiny shell in a sunny farm meadow."

    def build_structured_cover_prompt(self, *args, **kwargs):
        return "storybook cover prompt", "no text"

    async def _extract_character_description(self, *args, **kwargs):
        return "small yellow chick; blue scarf; curious and kind"

    async def generate_images(self, *args, **kwargs):
        return [
            SceneImage(scene_id="cover", image_url="https://offline.invalid/cover.jpg", prompt="cover", created_at="2026-01-01T00:00:00Z", seed=123),
            SceneImage(scene_id="scene-1", image_url="https://offline.invalid/scene-1.jpg", prompt="scene", created_at="2026-01-01T00:00:00Z", seed=123),
        ]

    async def validate_cover_image(self, *args, **kwargs):
        return {"passed": True, "issues": []}


async def main():
    source_module = story_tasks
    callback = OmoCallback()
    store = LocalArtifactStore(Path("/tmp/phonicsmaker-offline-probe"))
    task_service = OmoTaskService()

    with SourceRuntimeBoundary(source_module, store, callback):
        result = await source_module.generate_story_task(
            task_id="offline-draft-probe",
            phonemes=["sh", "ch"],
            story_idea="A chick finds a shiny shell.",
            difficulty_level="2",
            task_service=task_service,
            story_service_instance=OfflineStoryService(),
            image_service_instance=OfflineImageService(),
            draft_only=True,
            include_activities=False,
            include_audio=False,
            focus_phonemes=["sh", "ch"],
            language_variant="en_au",
            is_free=False,
            job=None,
        )

    assert result["story_title"] == "The Shiny Shell"
    assert len(result["scenes"]) == 2
    assert len(result["images"]) == 2
    assert result["phonemes"] == ["sh", "ch"]
    assert result["book_seed"] == 123
    assert any(event["type"] == "draft_completion" for event in callback.events)
    assert any(event["type"] == "result" for event in task_service.events)
    print({"status": "draft_ready", "provider_calls": 0, "scene_count": len(result["scenes"]), "image_count": len(result["images"]), "callback_events": len(callback.events)})


asyncio.run(main())
