# phonics_maker/tasks/story_tasks.py

import asyncio
import json
import os
import time
from pathlib import Path
from typing import List, Dict, Any, Optional
from app.core.config.logger import logger
from app.core.storage.file_storage import upload_result
from app.phonics_maker.task_management.task_service import TaskService
from app.phonics_maker.story_generation.story_service import StoryService
from app.phonics_maker.image_generation.image_service import (
    ImageService,
    flatten_character_descriptions,
)
from app.core.ai.ai_config import ai_config
from app.db.models.image import SceneImage
from app.phonics_maker.activity_generation.activity_service import ActivityService
from app.phonics_maker.pdf_generation import generate_story_pdf, get_task_temp_dir, cleanup_task_temp_dir, generate_default_layout_json
from app.phonics_maker.activity_generation.activity_types import ActivityConfig
from app.phonics_maker.audio_generation.audio_types import AudioConfig
from app.db.models.task import TaskStatus
from app.db.models.story import LanguageVariant
from app.core.error_handling.error_service import error_service
from app.core.callbacks.callback_service import callback_service
from app.core.config.config import settings
import runpod


DEBUG_DIR = Path("debug_data")  # For RunPod, this will be in /tmp or similar
DEBUG_DIR.mkdir(exist_ok=True)
EMAIL_TEMPLATE_DIR = Path("app/templates/emails")


def read_email_template(template_name: str) -> str:
    template_path = EMAIL_TEMPLATE_DIR / template_name
    try:
        with open(template_path, "r") as f:
            return f.read()
    except Exception as e:
        logger.error(f"Failed to read email template {template_name}: {e}")
        return "Your story is ready! Download it here: {$download_link}"


async def generate_story_task(
    task_id: str,
    phonemes: List[str],
    story_idea: str,
    difficulty_level: str,
    task_service: TaskService,
    story_service_instance: StoryService,
    image_service_instance: ImageService,
    is_free: Optional[bool] = False,
    debug_config: Optional[Dict[str, Any]] = None,
    user_email: Optional[str] = None,
    language_variant: Optional[LanguageVariant] = None,
    job: Optional[str] = None, # RunPod job object or ID
    include_activities: bool = False,  # NEW: Include activity worksheets at end of book
    activity_config: Optional[ActivityConfig] = None,  # NEW: Configuration for which activities to include
    include_audio: bool = False,  # DISABLED: Fish Audio 402 "Insufficient Balance" — re-enable when topped up
    audio_config: Optional[AudioConfig] = None,  # NEW: Audio generation settings
    illustration_style: Optional[str] = None,  # NEW: e.g. "vivid_cartoon", "soft_watercolor"
    story_type: Optional[str] = None,  # NEW: e.g. "narrative", "rhyming_poem"
    book_layout: Optional[str] = None,  # NEW: e.g. "classic", "picture_top", "side_by_side"
    book_font: Optional[str] = None,  # NEW: e.g. "comic_neue", "lexie_readable"
    # ── V2 fields (all optional for backward compatibility) ──
    known_phonemes: Optional[List[str]] = None,      # GPCs the student already knows
    focus_phonemes: Optional[List[str]] = None,      # 1-5 new GPCs being taught
    sight_words: Optional[List[str]] = None,          # Permitted irregular HFW
    strict_decodable: Optional[bool] = None,          # Every word must be decodable
    vocabulary_mode: Optional[str] = None,             # "decodable" | "instructional" | "authentic"
    focus_mode: Optional[str] = None,                 # "phonics" | "morphology" | "both"
    morphology_focus: Optional[List[str]] = None,     # Selected suffixes/prefixes
    story_format: Optional[str] = None,               # "storybook" | "passage"
    student_age: Optional[str] = None,                # Interest-level age
    year_level: Optional[str] = None,                 # Year/grade level for reading complexity
    curriculum: Optional[str] = None,                 # Curriculum code
    highlight_text: Optional[bool] = None,            # Highlight phonemes in rendered text
    series_info: Optional[Dict[str, Any]] = None,     # {book_position, total_books, series_name}
    book_title: Optional[str] = None,                   # AI-planned title for this book
    series_characters: Optional[List[Dict[str, Any]]] = None,  # Recurring characters
    series_theme: Optional[str] = None,                 # Overall series theme
    target_difficulties: Optional[List[str]] = None,    # NEW: Additional difficulty levels to generate concurrently
    draft_only: bool = False,                           # NEW: Skip PDF generation and return structured JSON
    standard_codes: Optional[List[str]] = None,         # Audit-proof curriculum standard tags
    character_pronouns: Optional[str] = None,           # "he/him" | "she/her" | "they/them"
    page_count: Optional[int] = None,                   # Override scene count (paid only; None → default 20)
    # ── Reference-book fields (reuse a past book's characters/style) ──
    reference_character_description: Optional[str] = None,  # Canonical character description inherited from a reference book
    reference_seed: Optional[int] = None,               # Book seed inherited from a reference book (same noise family)
) -> Dict[str, Optional[str]]:  # Returns a dict with PDF URL and Thumbnail URL (or draft data)
    
    # Define task_temp_dir for PDF generation intermediates at the beginning
    # This ensures it's available for the finally block
    base_temp_dir = Path("temp") # Assuming 'temp' is at the root like 'debug_data'
    base_temp_dir.mkdir(exist_ok=True)
    task_pdf_temp_dir = get_task_temp_dir(base_temp_dir, task_id)

    try:
        logger.info(f"Starting story generation for task {task_id}")
        pipeline_start = time.perf_counter()
        timing_stages = {}  # accumulate per-stage timings

        # Send initial progress
        await callback_service.send_progress(task_id, 5, "Starting story generation")
        if job:
            runpod.serverless.progress_update(job, 5)  # Initial progress

        debug_config = debug_config or {}
        start_from_step = debug_config.get("start_from_step")
        load_from_task_id = debug_config.get("load_from_task_id")
        save_intermediates = debug_config.get("save_intermediates", False)

        if user_email:
            # This might have been done at record creation, but ensure it
            await task_service.set_user_email_for_task(task_id, user_email)
            logger.info(f"Ensured task {task_id} has email {user_email}")

        story_title = None
        cover_image_prompt = None
        all_images = []
        short_scenes = []  # Initialize as empty list
        scene_image_prompts = []
        variations = {}    # Dict[str, tuple[str, List[str]]]

        if load_from_task_id:
            # _load_debug_data can remain as is, uses local file system
            previous_data = _load_debug_data(load_from_task_id)
            if previous_data:
                short_scenes = previous_data.get("short_scenes", [])
                story_title = previous_data.get("story_title")
                scene_image_prompts = previous_data.get("scene_image_prompts", [])
                cover_image_prompt = previous_data.get("cover_image_prompt")
                other_images_data = previous_data.get("all_images")
                if other_images_data:
                    all_images = [
                        SceneImage(**image_data) for image_data in other_images_data
                    ]
                logger.info(f"Loaded debug data from task {load_from_task_id}")

        # Send story generation progress
        await callback_service.send_progress(task_id, 15, "Generating story scenes")
        if job:
            runpod.serverless.progress_update(job, 15)  # Story generation progress

        if not start_from_step or start_from_step == "story":
            t0 = time.perf_counter()
            story_title, short_scenes = (
                await story_service_instance.generate_short_scenes(
                    story_idea, phonemes, difficulty_level, is_free, language_variant,
                    story_type=story_type,
                    known_phonemes=known_phonemes,
                    focus_phonemes=focus_phonemes,
                    sight_words=sight_words,
                    strict_decodable=strict_decodable,
                    vocabulary_mode=vocabulary_mode,
                    focus_mode=focus_mode,
                    morphology_focus=morphology_focus,
                    story_format=story_format,
                    student_age=student_age,
                    year_level=year_level,
                    curriculum=curriculum,
                    book_title=book_title,
                    series_characters=series_characters,
                    series_theme=series_theme,
                    series_info=series_info,
                    character_pronouns=character_pronouns,
                    page_count=page_count,
                )
            )
            _dt = time.perf_counter() - t0
            timing_stages['story_generation'] = _dt
            logger.info(f"⏱️  [TIMING] Story generation: {_dt:.2f}s")
            # ── Send intermediate data: story title + scene previews ──
            await callback_service.send_intermediate_data(task_id, {
                "phase": "writing",
                "story_title": story_title,
                "scene_count": len(short_scenes),
                "scene_snippets": [s[:120] for s in short_scenes[:3]],
                "focus_phonemes": focus_phonemes or [],
                "difficulty_level": difficulty_level,
                "illustration_style": illustration_style,
            })
            if save_intermediates:
                _save_debug_data(task_id, "short_scenes", short_scenes)
                _save_debug_data(task_id, "story_title", story_title)

            # ── DIFFERENTIATION: Generate parallel variations ──
            if target_difficulties and short_scenes:
                logger.info(f"Generating parallel variations for target difficulties: {target_difficulties}")
                diff_tasks = []
                for diff in target_difficulties:
                    diff_tasks.append(
                        story_service_instance.differentiate_story(
                            original_title=story_title,
                            original_scenes=short_scenes,
                            target_difficulty=diff,
                            language_variant=language_variant
                        )
                    )
                diff_results = await asyncio.gather(*diff_tasks, return_exceptions=True)
                for diff, result in zip(target_difficulties, diff_results):
                    if isinstance(result, Exception):
                        logger.error(f"Failed to differentiate for level {diff}: {result}")
                    else:
                        variations[diff] = result
        elif not short_scenes:
            raise ValueError(
                "Cannot skip short scene generation without provided scene data"
            )

        # ── Start activity generation early (runs in parallel with prompts + images) ──
        # Activities only need story text, not images — start now to overlap with I/O
        activity_task = None
        if include_activities:
            async def _generate_activities():
                svc = ActivityService()
                return await svc.generate_all_activities(
                    scenes=short_scenes,
                    phonemes=phonemes,
                    config=activity_config,
                    max_phonemes=5,
                    story_title=story_title,
                    difficulty_level=int(difficulty_level) if difficulty_level else 2,
                )
            activity_task = asyncio.create_task(_generate_activities())

        # Send cover + scene prompts progress
        await callback_service.send_progress(task_id, 25, "Creating image prompts")
        if job:
            runpod.serverless.progress_update(job, 25)

        # ── Cover prompt: Text-Strict Prompt Structure ─────────────────────
        # Gemini generates a rich visual description (80-120 words) which is:
        #   1. Plugged into the Text-Strict formula → cover_image_prompt (for Runware)
        #   2. Used as context for scene prompt generation & character extraction
        # This keeps the cover clean (title baked in by AI) AND preserves
        # character consistency across scenes.
        character_description = None
        cover_negative_prompt = None
        cover_visual_description = None  # rich character/scene desc for scene context

        if not start_from_step or start_from_step == "cover_prompt":
            t0 = time.perf_counter()
            # Use only focus phonemes + morphology for the cover badge (same
            # logic as pdf_service).  Falling back to the full `phonemes` list
            # produces an unreadably long badge on the AI-generated cover.
            cover_phonemes_for_prompt = list(focus_phonemes or []) + list(morphology_focus or [])
            cover_visual_description = await image_service_instance.generate_cover_visual_description(
                story_title, story_idea, short_scenes,
                illustration_style=illustration_style,
                student_age=student_age,
            )
            cover_image_prompt, cover_negative_prompt = (
                image_service_instance.build_structured_cover_prompt(
                    story_title,
                    cover_phonemes_for_prompt,
                    cover_visual_description,
                    illustration_style=illustration_style,
                )
            )
            _dt = time.perf_counter() - t0
            timing_stages['cover_prompt'] = _dt
            logger.info(f"⏱️  [TIMING] Cover image prompt (structured + Gemini visual desc): {_dt:.2f}s")
            if save_intermediates:
                _save_debug_data(task_id, "cover_image_prompt", cover_image_prompt)
                _save_debug_data(task_id, "cover_visual_description", cover_visual_description)
        elif not cover_image_prompt:
            raise ValueError(
                "Cannot skip cover image prompt generation without provided data"
            )
        else:
            # Debug resume path — rebuild negative prompt; visual desc unavailable
            cover_negative_prompt = image_service_instance.COVER_NEGATIVE_PROMPT
            cover_visual_description = cover_image_prompt  # best available fallback

        # ── Scene prompts + character extraction ──────────────────────────
        # Use cover_visual_description (rich character details) as context for
        # scene prompts and character extraction — NOT the structured cover
        # prompt which is full of Text-Strict boilerplate.
        character_ref_url = None

        if not start_from_step or start_from_step == "scene_prompts":
            t0 = time.perf_counter()
            # If a reference book supplied a character description, reuse it verbatim and
            # skip the extraction call; otherwise extract from the VISUAL description (rich details).
            if reference_character_description:
                logger.info("Reusing character description from reference book (skipping extraction)")
                character_description = reference_character_description
                char_desc_task = None
            else:
                char_desc_task = image_service_instance._extract_character_description(
                    cover_visual_description, short_scenes, student_age=student_age
                )

            if image_service_instance.use_ace_plus_plus and story_idea and cover_image_prompt:
                # Run scene prompts + char ref image + char description concurrently
                logger.info("Running scene prompt generation + ACE++ char ref + char description in parallel...")
                scene_prompts_task = story_service_instance.generate_scene_image_prompts(
                    story_idea, short_scenes, cover_visual_description,
                    illustration_style=illustration_style,
                    student_age=student_age,
                )
                char_ref_task = image_service_instance.generate_character_reference_image(
                    story_idea, cover_visual_description, student_age=student_age
                )
                if char_desc_task is not None:
                    scene_image_prompts, character_ref_url, character_description = await asyncio.gather(
                        scene_prompts_task, char_ref_task, char_desc_task
                    )
                else:
                    scene_image_prompts, character_ref_url = await asyncio.gather(
                        scene_prompts_task, char_ref_task
                    )
            else:
                # Run scene prompts + char description concurrently
                logger.info("Running scene prompt generation + char description in parallel...")
                scene_prompts_task = story_service_instance.generate_scene_image_prompts(
                    story_idea, short_scenes, cover_visual_description,
                    illustration_style=illustration_style,
                    student_age=student_age,
                )
                if char_desc_task is not None:
                    scene_image_prompts, character_description = await asyncio.gather(
                        scene_prompts_task, char_desc_task
                    )
                else:
                    scene_image_prompts = await scene_prompts_task
            _dt = time.perf_counter() - t0
            timing_stages['scene_prompts_and_char'] = _dt
            logger.info(f"⏱️  [TIMING] Scene prompts + char description (parallel): {_dt:.2f}s")
            if save_intermediates:
                _save_debug_data(task_id, "scene_image_prompts", scene_image_prompts)

        # Send image generation progress
        await callback_service.send_progress(task_id, 45, "Generating images with character consistency")
        if job:
            runpod.serverless.progress_update(job, 45)  # Image generation progress

        if not start_from_step or start_from_step == "images":
            t0 = time.perf_counter()
            # Pass story_idea for ACE++ character reference generation
            # Pass pre-computed character_description to skip internal LLM call
            all_images = await image_service_instance.generate_images(
                cover_image_prompt,
                scene_image_prompts,
                is_free,
                story_idea=story_idea,
                illustration_style=illustration_style,
                student_age=student_age,
                character_ref_url=character_ref_url,  # Pre-computed (or None if ACE++ disabled)
                character_description=character_description,  # Pre-computed to skip internal LLM call
                reference_seed=reference_seed,  # Inherited from a reference book (or None)
                cover_negative_prompt=cover_negative_prompt,
                cache_dir=str(task_pdf_temp_dir),  # Cache validated images to avoid re-downloading in PDF stage
            )
            _dt = time.perf_counter() - t0
            timing_stages['image_generation'] = _dt
            logger.info(f"⏱️  [TIMING] Image generation: {_dt:.2f}s")
            # ── Send intermediate data: cover image + all preview images ──
            if all_images:
                cover_url = all_images[0].image_url if all_images else None
                preview_urls = [img.image_url for img in all_images]  # all images for full preview strip
                await callback_service.send_intermediate_data(task_id, {
                    "phase": "illustrating",
                    "story_title": story_title,
                    "scene_count": len(short_scenes),
                    "cover_image_url": cover_url,
                    "preview_images": preview_urls,
                    "illustration_style": illustration_style,
                })

            # ── Cover validation + activity generation (parallel) ────────
            # Cover validation is I/O-bound (Gemini API), activity gen is
            # CPU-bound — run them concurrently so validation is "free".

            async def _validate_and_fix_cover():
                """Validate cover image, regenerate if garbled text found.

                Strategy: Validate the original cover first. If it fails, generate
                backup candidates and validate them. Lazy generation saves
                API costs and concurrent GPU capacity in the normal case where
                the original cover is correct.
                """
                NUM_SPECULATIVE = 2

                t_start = time.perf_counter()

                # ── Round 1: validate original cover ──
                try:
                    validation = await image_service_instance.validate_cover_image(
                        image_url=all_images[0].image_url,
                        expected_title=story_title,
                        cover_prompt=cover_image_prompt,
                        local_path=all_images[0].cached_path,
                    )
                except Exception as e:
                    logger.warning(f"Cover validation failed: {e}")
                    validation = {"passed": True, "issues": []}

                logger.info(f"⏱️  [TIMING] Cover validation: {time.perf_counter() - t_start:.2f}s")

                if validation.get("passed", True):
                    return  # Original cover is fine

                logger.warning(
                    f"Cover image failed validation: {validation.get('issues', [])}"
                )

                # ── Round 2: Generate backups (lazy) ──
                logger.info(f"Generating {NUM_SPECULATIVE} backup cover images...")
                t_regen = time.perf_counter()
                backup_coros = [
                    ai_config.generate_image(
                        cover_image_prompt, is_free,
                        extra_negative_prompt=cover_negative_prompt,
                    )
                    for _ in range(NUM_SPECULATIVE)
                ]
                regen_results = await asyncio.gather(*backup_coros, return_exceptions=True)
                backup_urls = [r for r in regen_results if isinstance(r, str)]
                logger.info(f"⏱️  [TIMING] Cover backup generation: {time.perf_counter() - t_regen:.2f}s")

                # ── Validate backup candidates ──
                if backup_urls:
                    t_val = time.perf_counter()
                    val_results = await asyncio.gather(*[
                        image_service_instance.validate_cover_image(
                            image_url=url,
                            expected_title=story_title,
                            cover_prompt=cover_image_prompt,
                        )
                        for url in backup_urls
                    ])
                    logger.info(f"⏱️  [TIMING] Cover backup validation ({len(backup_urls)} candidates): {time.perf_counter() - t_val:.2f}s")

                    for url, val in zip(backup_urls, val_results):
                        if val.get("passed", True):
                            all_images[0] = SceneImage(
                                scene_id="cover",
                                image_url=url,
                                prompt=cover_image_prompt,
                                created_at=all_images[0].created_at,
                            )
                            return

                    # None passed — use best backup (best effort, limit to 1 round for speed)
                    all_images[0] = SceneImage(
                        scene_id="cover",
                        image_url=backup_urls[-1],
                        prompt=cover_image_prompt,
                        created_at=all_images[0].created_at,
                    )


            # Start cover validation as a background task
            cover_validation_task = asyncio.create_task(_validate_and_fix_cover())
            # ─────────────────────────────────────────────────────────────

            if save_intermediates:
                serializable_scene_images = [image.model_dump() for image in all_images]
                _save_debug_data(task_id, "all_images", serializable_scene_images)
        elif not all_images:
            raise ValueError("Cannot skip image generation without provided image data")
        else:
            cover_validation_task = None

        # ── Collect activity results (started earlier, in parallel with prompts + images) ──
        activity_data = []
        answer_key = None
        answer_key_obj = None  # Keep AnswerKeyData object for PDF reuse
        if activity_task is not None:
            try:
                activity_data, answer_key_obj = await activity_task
                answer_key = answer_key_obj.__dict__ if answer_key_obj else None
            except Exception as e:
                logger.error(f"Early activity generation failed, falling back to inline: {e}")
                activity_service = ActivityService()
                activity_data, answer_key_obj = await activity_service.generate_all_activities(
                    scenes=short_scenes,
                    phonemes=phonemes,
                    config=activity_config,
                    max_phonemes=5,
                    story_title=story_title,
                    difficulty_level=int(difficulty_level) if difficulty_level else 2,
                )
                answer_key = answer_key_obj.__dict__ if answer_key_obj else None

        # Wait for cover validation to finish before building draft payload
        if cover_validation_task is not None:
            await cover_validation_task

        # Persist/display a clean description without the extraction scaffolding.
        persisted_character_description = flatten_character_descriptions(character_description)

        draft_payload = {
            "story_title": story_title,
            "scenes": short_scenes,
            "images": [img.model_dump() for img in all_images] if all_images else [],
            "phonemes": phonemes,
            "activities": activity_data,
            "answer_key": answer_key,
            "variations": variations,
            "book_layout": book_layout,
            "book_font": book_font,
            "illustration_style": illustration_style,
            "difficulty_level": difficulty_level,
            "is_free": is_free,
            "include_activities": include_activities,
            "series_info": series_info,
            "focus_phonemes": focus_phonemes,
            "highlight_text": highlight_text,
            "morphology_focus": morphology_focus,
            # ── Reference-book fields: let this book be reused as a reference for the next one ──
            "character_description": persisted_character_description,
            "book_seed": image_service_instance._book_seed,
            "characters": (
                [{"name": "", "role": "protagonist", "appearance": persisted_character_description, "personality": ""}]
                if persisted_character_description else []
            ),
        }
        
        if save_intermediates:
            _save_debug_data(task_id, "draft_payload", draft_payload)
        
        # Always persist draft_data to disk so it survives server restarts
        try:
            draft_dir = Path(__file__).resolve().parent.parent.parent.parent / "draft_data"
            draft_dir.mkdir(exist_ok=True)
            draft_filepath = draft_dir / f"{task_id}.json"
            with open(draft_filepath, "w") as f:
                json.dump(draft_payload, f)
            logger.info(f"💾 Persisted draft_data to {draft_filepath}")
        except Exception as e:
            logger.warning(f"⚠️ Failed to persist draft_data to disk: {e}")

        if draft_only:
            # ── DRAFT MODE: Return structured JSON instead of generating PDF ──
            await callback_service.send_progress(task_id, 80, "Generating draft worksheets")
            
            await callback_service.send_progress(task_id, 100, "Draft ready")
            await callback_service.send_draft_completion(task_id, draft_data=draft_payload)
            
            # Update DB directly with draft completion
            task_service.set_task_result(
                task_id,
                current_user_email=user_email,
                status=TaskStatus.DRAFT_READY,
                metadata_update={
                    "progress": 100,
                    "completedAt": int(time.time() * 1000),
                    "message": "Draft generated successfully",
                    "draft_data": draft_payload,
                }
            )

            logger.info(f"Task {task_id} completed successfully in DRAFT MODE")
            return draft_payload

        # Send PDF generation progress
        # Build activity summary for frontend display
        activity_types = [a.get("activity_type", "").replace("_", " ").title() for a in activity_data] if activity_data else []
        # Include validated cover URL + updated preview images (cover may have changed after Gemini validation)
        validated_cover_url = all_images[0].image_url if all_images else None
        validated_preview_urls = [img.image_url for img in all_images] if all_images else None
        await callback_service.send_intermediate_data(task_id, {
            "phase": "assembling",
            "activity_count": len(activity_data) if activity_data else 0,
            "activity_types": activity_types,
            "cover_image_url": validated_cover_url,
            "preview_images": validated_preview_urls,
        })
        await callback_service.send_progress(task_id, 65, "Generating PDF")
        if job:
            runpod.serverless.progress_update(job, 65)  # PDF generation progress

        if not start_from_step or start_from_step == "pdf":
            t0 = time.perf_counter()
            # generate_story_pdf now returns a PDFGenerationResponse object
            # which includes pdf_url (local path) and thumbnail_local_path (local path)
            
            pdf_kwargs = dict(
                is_free=is_free,
                include_activities=include_activities,
                activity_config=activity_config,
                include_audio=False,  # DISABLED: Fish Audio 402 "Insufficient Balance" — wastes ~11s on share link timeout + failed API call
                audio_config=audio_config,
                language_variant=language_variant,
                book_layout=book_layout,
                book_font=book_font,
                focus_phonemes=focus_phonemes,
                highlight_text=highlight_text,
                illustration_style=illustration_style,
                morphology_focus=morphology_focus,
                series_info=series_info,
                standard_codes=standard_codes,
            )

            pdf_tasks = []
            
            # Base PDF — pass pre-generated activities to avoid regenerating them
            _pre_activities = (activity_data, answer_key_obj) if answer_key_obj else None
            pdf_tasks.append(
                generate_story_pdf(
                    task_id,
                    story_title,
                    short_scenes,
                    all_images,
                    phonemes,
                    difficulty_level,
                    pre_generated_activities=_pre_activities,
                    **pdf_kwargs
                )
            )

            # Variation PDFs (e.g. for differentiation)
            for diff, (diff_title, diff_scenes) in variations.items():
                pdf_tasks.append(
                    generate_story_pdf(
                        f"{task_id}_{diff.replace(' ', '_')}",
                        diff_title,
                        diff_scenes,
                        all_images,
                        phonemes,
                        diff,
                        with_print_variant=False,
                        **pdf_kwargs
                    )
                )

            pdf_results = await asyncio.gather(*pdf_tasks)
            pdf_generation_response = pdf_results[0]
            
            variations_pdf_responses = {
                diff: res for diff, res in zip(variations.keys(), pdf_results[1:])
            }

            _dt = time.perf_counter() - t0
            timing_stages['pdf_generation'] = _dt
            logger.info(f"⏱️  [TIMING] PDF generation (all): {_dt:.2f}s")
        else:
            pdf_data_loaded = _load_debug_data(load_from_task_id).get("pdf_generation_response") # Changed key
            if pdf_data_loaded:
                from app.db.models.pdf import PDFGenerationResponse
                pdf_generation_response = PDFGenerationResponse(**pdf_data_loaded)
            else:
                raise ValueError(
                    "Cannot skip PDF generation without provided PDF data or loaded data"
                )
            variations_pdf_responses = {}

        # Send upload progress
        t0 = time.perf_counter()
        await callback_service.send_intermediate_data(task_id, {"phase": "uploading"})
        await callback_service.send_progress(task_id, 85, "Uploading files")
        if job:
            runpod.serverless.progress_update(job, 85)  # Upload progress

        if save_intermediates:
            _save_debug_data(task_id, "pdf_generation_response", pdf_generation_response.model_dump()) # Changed key

        pdf_local_path = pdf_generation_response.pdf_url
        pdf_compressed_local_path = pdf_generation_response.pdf_compressed_url
        thumbnail_local_path = pdf_generation_response.thumbnail_local_path
        worksheets_local_path = pdf_generation_response.worksheets_pdf_url
        book_only_local_path = pdf_generation_response.book_only_pdf_url
        homework_local_path = pdf_generation_response.homework_pdf_url
        answer_key_local_path = pdf_generation_response.answer_key_pdf_url
        pptx_local_path = pdf_generation_response.pptx_url

        uploaded_variations = {} # To store the final uploaded combined PDFs mapped by level

        # ── OPTIMISATION: Upload all files concurrently ────────────────
        logger.info(f"📦 Individual PDFs for task {task_id}:")
        logger.info(f"  combined:   {pdf_local_path} (exists={os.path.exists(pdf_local_path) if pdf_local_path else False})")
        logger.info(f"  book_only:  {book_only_local_path} (exists={os.path.exists(book_only_local_path) if book_only_local_path else False})")
        logger.info(f"  worksheets: {worksheets_local_path} (exists={os.path.exists(worksheets_local_path) if worksheets_local_path else False})")
        logger.info(f"  homework:   {homework_local_path} (exists={os.path.exists(homework_local_path) if homework_local_path else False})")
        logger.info(f"  answer_key: {answer_key_local_path} (exists={os.path.exists(answer_key_local_path) if answer_key_local_path else False})")
        logger.info(f"  thumbnail:  {thumbnail_local_path} (exists={os.path.exists(thumbnail_local_path) if thumbnail_local_path else False})")
        logger.info(f"  pptx:       {pptx_local_path} (exists={os.path.exists(pptx_local_path) if pptx_local_path else False})")

        if settings.LOCAL_MODE:
            # ── LOCAL DEV: Serve files directly instead of uploading ──
            import shutil
            base_dir = Path(__file__).resolve().parent.parent.parent.parent
            output_dir = base_dir / "static" / "output" / task_id
            output_dir.mkdir(parents=True, exist_ok=True)

            def _local_url(local_path, label, prefix=""):
                """Copy file to static output dir and return localhost URL."""
                if not local_path or not os.path.exists(local_path):
                    return None
                filename = prefix + Path(local_path).name
                dest = output_dir / filename
                shutil.copy2(local_path, dest)
                url = f"http://localhost:8000/output/{task_id}/{filename}"
                logger.info(f"LOCAL_MODE: Serving {label} at {url}")
                return url

            # Create default layout JSON
            layout_data = generate_default_layout_json(
                task_id=task_id,
                story_title=story_title,
                scenes=short_scenes,
                images=all_images,
                difficulty_level=difficulty_level,
                focus_phonemes=focus_phonemes
            )
            layout_temp_path = Path(pdf_local_path).parent / f"pdf_data_{task_id}.json"
            with open(layout_temp_path, "w") as f:
                json.dump(layout_data, f)

            uploaded_pdf_url = _local_url(pdf_local_path, "combined PDF")
            uploaded_pdf_compressed_url = _local_url(pdf_compressed_local_path, "print-friendly PDF")
            uploaded_book_only_url = _local_url(book_only_local_path, "book-only PDF")
            uploaded_worksheets_url = _local_url(worksheets_local_path, "worksheets PDF")
            uploaded_homework_url = _local_url(homework_local_path, "homework PDF")
            uploaded_answer_key_url = _local_url(answer_key_local_path, "answer key PDF")
            uploaded_thumbnail_url = _local_url(thumbnail_local_path, "thumbnail")
            uploaded_pptx_url = _local_url(pptx_local_path, "PPTX")
            _local_url(layout_temp_path, "layout JSON")
            
            for diff, v_res in variations_pdf_responses.items():
                uploaded_variations[diff] = _local_url(v_res.pdf_url, f"variation {diff} combined", prefix=f"{diff.replace(' ', '_')}_")

        else:
            # ── PRODUCTION: Upload to DigitalOcean Spaces ────────────
            async def _safe_upload(local_path, label, max_retries=3):
                """Upload a file with retry logic. Returns (url, local_path) or (None, None)."""
                if not local_path or not os.path.exists(local_path):
                    return None, None
                for attempt in range(1, max_retries + 1):
                    try:
                        url = await upload_result(local_path, task_id)
                        logger.info(f"Uploaded {label} for task {task_id}: {url}")
                        return url, local_path
                    except Exception as e:
                        logger.error(f"Upload {label} attempt {attempt}/{max_retries} failed for task {task_id}: {str(e)}")
                        if attempt < max_retries:
                            delay = 2 ** attempt  # 2s, 4s
                            logger.info(f"Retrying {label} upload in {delay}s...")
                            await asyncio.sleep(delay)
                logger.error(f"All {max_retries} upload attempts failed for {label} (task {task_id})")
                return None, None

            # Create default layout JSON
            layout_data = generate_default_layout_json(
                task_id=task_id,
                story_title=story_title,
                scenes=short_scenes,
                images=all_images,
                difficulty_level=difficulty_level,
                focus_phonemes=focus_phonemes
            )
            layout_temp_path = Path(pdf_local_path).parent / f"pdf_data_{task_id}.json"
            with open(layout_temp_path, "w") as f:
                json.dump(layout_data, f)

            upload_tasks = [
                _safe_upload(pdf_local_path, "combined PDF"),
                _safe_upload(pdf_compressed_local_path, "print-friendly PDF"),
                _safe_upload(book_only_local_path, "book-only PDF"),
                _safe_upload(worksheets_local_path, "worksheets PDF"),
                _safe_upload(homework_local_path, "homework PDF"),
                _safe_upload(answer_key_local_path, "answer key PDF"),
                _safe_upload(thumbnail_local_path, "thumbnail"),
                _safe_upload(pptx_local_path, "PPTX"),
            ]

            var_keys = list(variations_pdf_responses.keys())
            for diff in var_keys:
                upload_tasks.append(_safe_upload(variations_pdf_responses[diff].pdf_url, f"variation {diff} combined PDF"))

            # Append layout JSON at the end
            upload_tasks.append(_safe_upload(layout_temp_path, "layout JSON"))

            # Compute deterministic public URLs upfront
            bucket_name = settings.SPACES_NAME
            cdn_endpoint = settings.SPACES_CDN_ENDPOINT or settings.SPACES_ENDPOINT

            def get_public_url(local_path):
                if not local_path:
                    return None
                filename = os.path.basename(local_path)
                return f"https://{bucket_name}.{cdn_endpoint}/generated_pdfs/{task_id}/{filename}"

            uploaded_pdf_url = get_public_url(pdf_local_path)
            uploaded_pdf_compressed_url = get_public_url(pdf_compressed_local_path)
            uploaded_book_only_url = get_public_url(book_only_local_path)
            uploaded_worksheets_url = get_public_url(worksheets_local_path)
            uploaded_homework_url = get_public_url(homework_local_path)
            uploaded_answer_key_url = get_public_url(answer_key_local_path)
            uploaded_thumbnail_url = get_public_url(thumbnail_local_path)
            uploaded_pptx_url = get_public_url(pptx_local_path)
            
            uploaded_variations = {}
            for diff in var_keys:
                uploaded_variations[diff] = get_public_url(variations_pdf_responses[diff].pdf_url)

            # Spawn uploads in a background task
            async def _background_upload_task():
                t_bg_start = time.perf_counter()
                try:
                    logger.info(f"Starting background uploads for task {task_id}...")
                    upload_results = await asyncio.gather(*upload_tasks)
                    # Clean up local files after all uploads complete
                    for url, local_path in upload_results:
                        if local_path and os.path.exists(local_path):
                            try:
                                os.remove(local_path)
                            except OSError:
                                pass
                    # Clean up temp directory
                    import shutil
                    if os.path.exists(task_pdf_temp_dir):
                        try:
                            shutil.rmtree(task_pdf_temp_dir)
                        except OSError:
                            pass
                    logger.info(f"⏱️  [TIMING] Background upload completed successfully in {time.perf_counter() - t_bg_start:.2f}s for task {task_id}")
                except Exception as e:
                    logger.error(f"Background upload failed for task {task_id}: {str(e)}")

            asyncio.create_task(_background_upload_task())
        
        # Email delivery is handled by the Next.js /api/job-done callback route.
        # It sends the appropriate email (free book template or paid user template)
        # when it receives the completion callback below.
        if user_email:
            logger.info(f"Email for task {task_id} will be sent by callback receiver to {user_email}")

        if save_intermediates:
            _save_debug_data(task_id, "complete_pdf_url", uploaded_pdf_url)
            if uploaded_thumbnail_url:
                _save_debug_data(task_id, "complete_thumbnail_url", uploaded_thumbnail_url)


        # Send completion callback
        await callback_service.send_completion(
            task_id, uploaded_pdf_url, uploaded_thumbnail_url,
            uploaded_worksheets_url, uploaded_book_only_url,
            uploaded_homework_url, uploaded_answer_key_url,
            uploaded_pptx_url,
            variations=uploaded_variations,
            pdf_compressed_url=uploaded_pdf_compressed_url
        )
        if job:
            runpod.serverless.progress_update(job, 100)  # Final progress

        task_service.set_task_result(
            task_id, 
            pdf_url=uploaded_pdf_url, 
            thumbnail_url=uploaded_thumbnail_url, # Pass thumbnail URL
            current_user_email=user_email,
            status=TaskStatus.COMPLETED,
            metadata_update={
                "progress": 100,
                "completedAt": int(time.time() * 1000),
                "message": "Generation completed successfully",
                "worksheets_url": uploaded_worksheets_url,
                "book_only_url": uploaded_book_only_url,
                "homework_url": uploaded_homework_url,
                "answer_key_url": uploaded_answer_key_url,
                "pptx_url": uploaded_pptx_url,
                "pdf_compressed_url": uploaded_pdf_compressed_url,
                "variations": uploaded_variations,
                "draft_data": draft_payload,
            }
        )

        _dt = time.perf_counter() - t0
        timing_stages['upload'] = _dt
        logger.info(f"⏱️  [TIMING] Upload queue dispatch: {_dt:.2f}s")
        total_time = time.perf_counter() - pipeline_start
        timing_stages['TOTAL'] = total_time
        logger.info(f"⏱️  [TIMING] ══ TOTAL PIPELINE: {total_time:.2f}s ══")

        # Write timing summary to file so it's never lost to terminal scroll
        try:
            summary_lines = [f"\n{'='*50}", f"TIMING SUMMARY — task {task_id}", f"{'='*50}"]
            for stage, dt in timing_stages.items():
                bar = '█' * int(dt / total_time * 30) if total_time > 0 else ''
                pct = dt / total_time * 100 if total_time > 0 else 0
                summary_lines.append(f"  {stage:30s} {dt:7.2f}s  ({pct:4.1f}%)  {bar}")
            summary_lines.append(f"{'='*50}\n")
            summary_text = '\n'.join(summary_lines)
            logger.info(summary_text)
            with open(Path(__file__).resolve().parent.parent.parent.parent / 'timing_summary.txt', 'a') as f:
                f.write(summary_text + '\n')
        except Exception:
            pass  # non-fatal

        logger.info(f"Task {task_id} completed successfully. PDF: {uploaded_pdf_url}, Thumbnail: {uploaded_thumbnail_url}, Worksheets: {uploaded_worksheets_url}, Book-only: {uploaded_book_only_url}")
        
        # Ensure we always provide the draft payload so the frontend can opt-in to editing AFTER generating
        return {
            "pdf_url": uploaded_pdf_url, 
            "thumbnail_url": uploaded_thumbnail_url,
            "book_only_url": uploaded_book_only_url,  # Book without worksheets
            "worksheets_url": uploaded_worksheets_url,  # Worksheets only
            "homework_url": uploaded_homework_url,  # Worksheets without answer key (student homework)
            "answer_key_url": uploaded_answer_key_url,  # Answer key only (teacher copy)
            "pptx_url": uploaded_pptx_url,  # PowerPoint for smartboard display
            "pdf_compressed_url": uploaded_pdf_compressed_url,  # Print-friendly combined PDF (smaller file)
            "scenes": short_scenes,  # Retained for backwards compatibility
            "phonemes": phonemes,     # Retained for backwards compatibility
            "audio_manifest": pdf_generation_response.audio_manifest,  # Audio narration data (or None)
            "draft_data": draft_payload, # Critical for WYSIWYG Editor selection
        }

    except Exception as e:
        error_service.log_error(e, context=f"Task {task_id} failed")
        
        # Send error callback
        await callback_service.send_error(task_id, str(e))
        
        # TaskService.set_task_result will update status to FAILED if it's not COMPLETED
        # We need to ensure this happens even on failure, if not already set to COMPLETED.
        # However, the current set_task_result only sets to COMPLETED. 
        # A separate method or logic might be needed for FAILED status or rely on the calling handler.
        # For now, we'll re-raise and let the handler manage the final status update on error.
        raise Exception(f"Story generation failed for task {task_id}: {str(e)}") from e
    finally:
        # Clean up the task-specific temporary directory used by PDF generation
        if task_pdf_temp_dir and task_pdf_temp_dir.exists():
            logger.info(f"Cleaning up temporary PDF generation directory: {task_pdf_temp_dir}")
            cleanup_task_temp_dir(task_pdf_temp_dir)


def _save_debug_data(task_id: str, key: str, data: Any) -> None:
    task_dir = DEBUG_DIR / task_id
    task_dir.mkdir(exist_ok=True)
    with open(task_dir / f"{key}.json", "w") as f:
        json.dump(data, f, indent=2)


def _load_debug_data(task_id: str) -> Dict[str, Any]:
    task_dir = DEBUG_DIR / task_id
    if not task_dir.exists():
        logger.warning(f"No debug data found for task {task_id}")
        return {}
    result = {}
    for file_path in task_dir.glob("*.json"):
        key = file_path.stem
        try:
            with open(file_path, "r") as f:
                result[key] = json.load(f)
        except Exception as e:
            logger.error(f"Failed to load {file_path}: {e}")
    return result
