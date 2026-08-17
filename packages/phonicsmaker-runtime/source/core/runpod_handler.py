# handler.py

# Load and validate config early - must be first
from app.core.config.validation import load_and_validate_config
load_and_validate_config()

import runpod
import uuid
from typing import Dict, Any, Optional

from app.core.config.logger import logger, set_task_id
from app.db.database import session_scope  # To get DB session for UserService
from app.core.user.user_service import UserService
from app.phonics_maker.tasks.story_tasks import generate_story_task
from app.phonics_maker.task_management.task_service import TaskService
from app.phonics_maker.story_generation.story_service import StoryService
from app.phonics_maker.image_generation.image_service import ImageService
from app.core.error_handling.error_service import error_service
from app.core.config.config import settings

# Initialize services that don't require job-specific data here
# Or instantiate them inside the handler if they need job input for init
task_service = TaskService()
story_service_instance = StoryService()
image_service_instance = ImageService()


async def process_job(job: Dict[str, Any]) -> Dict[str, Any]:
    """
    Processes a single story generation job.
    """
    job_input = job.get("input", {})

    # --- API Key Authentication ---
    if settings.API_KEY:
        submitted_api_key = job_input.get("api_key")
        if not submitted_api_key or submitted_api_key != settings.API_KEY:
            logger.error("Invalid or missing API key.")
            return {"error": "Forbidden: Invalid API key", "status_code": 403}
    # ---

    phonemes = job_input.get("phonemes")
    story_idea = job_input.get("story_idea")
    difficulty_level = job_input.get("difficulty_level")
    is_free = job_input.get("is_free", False)
    user_email = job_input.get("user_email")
    language_variant = job_input.get("language_variant")
    debug_config = job_input.get("debug_config")  # For advanced debugging
    
    # Activity worksheet configuration
    include_activities = job_input.get("include_activities", False)
    activity_config_input = job_input.get("activity_config")
    
    # Convert activity config dict to ActivityConfig object if provided
    activity_config = None
    if include_activities and activity_config_input:
        from app.phonics_maker.activity_generation.activity_types import ActivityConfig
        activity_config = ActivityConfig(
            include_word_hunt=activity_config_input.get("include_word_hunt", True),
            include_sound_matching=activity_config_input.get("include_sound_matching", True),
            include_fill_in_blank=activity_config_input.get("include_fill_in_blank", True),
            include_tracing=activity_config_input.get("include_tracing", True),
            include_circle_sound=activity_config_input.get("include_circle_sound", False),
            include_word_scramble=activity_config_input.get("include_word_scramble", False),
            include_cut_and_sort=activity_config_input.get("include_cut_and_sort", False),
            include_sentence_building=activity_config_input.get("include_sentence_building", False),
            include_phoneme_spotter=activity_config_input.get("include_phoneme_spotter", False),
            include_rhyming_pairs=activity_config_input.get("include_rhyming_pairs", False),
            include_phoneme_position=activity_config_input.get("include_phoneme_position", False),
            include_sound_swap=activity_config_input.get("include_sound_swap", False),
            include_syllable_count=activity_config_input.get("include_syllable_count", False),
            include_word_ladder=activity_config_input.get("include_word_ladder", False),
            include_read_and_draw=activity_config_input.get("include_read_and_draw", False),
            include_phoneme_count=activity_config_input.get("include_phoneme_count", False),
            include_odd_one_out=activity_config_input.get("include_odd_one_out", False),
            include_missing_sound=activity_config_input.get("include_missing_sound", False),
            include_real_or_nonsense=activity_config_input.get("include_real_or_nonsense", False),
            include_word_building=activity_config_input.get("include_word_building", False),
            include_crossword=activity_config_input.get("include_crossword", False),
            include_comprehension_questions=activity_config_input.get("include_comprehension_questions", True),
            include_vocabulary_building=activity_config_input.get("include_vocabulary_building", True),
            include_synonyms=activity_config_input.get("include_synonyms", True),
            include_inferred_meaning=activity_config_input.get("include_inferred_meaning", True),
        )

    # Audio narration configuration
    # DISABLED: Fish Audio API returns 402 "Insufficient Balance", causing ~1.5 min
    # retry loop bottleneck. Commenting out until balance is topped up.
    # include_audio = job_input.get("include_audio", True)
    include_audio = False

    # Book customisation
    illustration_style = job_input.get("illustration_style")  # e.g. "vivid_cartoon", "soft_watercolor"
    story_type = job_input.get("story_type")  # e.g. "narrative", "rhyming_poem"
    book_layout = job_input.get("book_layout")  # e.g. "classic", "picture_top", "side_by_side"
    book_font = job_input.get("book_font")  # e.g. "comic_neue", "lexie_readable"
    logger.info(f"[RUNPOD] book_layout={book_layout!r}, book_font={book_font!r}")

    # V2 fields (optional, backward-compatible)
    known_phonemes = job_input.get("known_phonemes")      # GPCs the student already knows
    focus_phonemes = job_input.get("focus_phonemes")      # 1-5 new GPCs being taught
    sight_words = job_input.get("sight_words")            # Permitted irregular HFW
    strict_decodable = job_input.get("strict_decodable")  # Every word must be decodable
    vocabulary_mode = job_input.get("vocabulary_mode")    # "decodable" | "instructional" | "authentic"
    focus_mode = job_input.get("focus_mode")              # "phonics" | "morphology" | "both"
    morphology_focus = job_input.get("morphology_focus")  # Selected suffixes/prefixes
    story_format = job_input.get("story_format")          # "storybook" | "passage"
    student_age = job_input.get("student_age")            # Interest-level age
    curriculum = job_input.get("curriculum")              # Curriculum code
    highlight_text = job_input.get("highlight_text")      # Highlight phonemes in rendered text
    series_info = job_input.get("series_info")            # {book_position, total_books, series_name}
    character_pronouns = job_input.get("character_pronouns")  # "he/him" | "she/her" | "they/them"
    # Reference-book fields (reuse a past book's characters/style)
    reference_task_id = job_input.get("reference_task_id")
    reference_character_description = job_input.get("reference_character_description")
    reference_seed = job_input.get("reference_seed")

    if reference_task_id and not reference_character_description:
        ref_desc, ref_seed = task_service.get_reference_book_fields(reference_task_id, user_email)
        reference_character_description = ref_desc
        reference_seed = reference_seed if reference_seed is not None else ref_seed

    if not all([phonemes, story_idea, difficulty_level]):
        logger.error(
            "Missing required fields: phonemes, story_idea, or difficulty_level."
        )
        return {"error": "Missing required fields", "status_code": 400}

    task_id = job["id"]

    # Only for testing
    if settings.ENVIRONMENT == "development" and task_id == "local_test":
        task_id = str(uuid.uuid4())
    user_db_id: Optional[str] = None
    if user_email:
        try:
            # Get user_id from email for DB record (if user exists)
            with session_scope() as db:
                user_svc_instance = UserService(db)
                user_db_id = await user_svc_instance.get_user_id_by_email(user_email)
        except ValueError:  # User not found by email
            logger.info(
                f"User with email {user_email} not found, proceeding without user_db_id."
            )
        except Exception as e:
            logger.error(f"Error fetching user_id for {user_email}: {str(e)}")
            # Continue without user_db_id, but log error

    # Create initial DB record for the task
    try:
        task_service.create_task_record(
            task_id=task_id,
            user_id=user_db_id,
            phonemes=phonemes,
            story_idea=story_idea,
            difficulty_level=difficulty_level,
            is_free=is_free,
            user_email=user_email,
            language_variant=language_variant,
        )
    except Exception as e:
        # Log and continue, main task failure will be caught later
        logger.error(f"Failed to create initial task record for {task_id}: {str(e)}")

    try:
        # generate_story_task now returns a dictionary
        result_data = await generate_story_task(
            task_id=task_id,
            phonemes=phonemes,
            story_idea=story_idea,
            difficulty_level=difficulty_level,
            task_service=task_service,
            story_service_instance=story_service_instance,
            image_service_instance=image_service_instance,
            is_free=is_free,
            debug_config=debug_config,
            user_email=user_email,
            language_variant=language_variant,
            job=job,
            include_activities=include_activities,
            activity_config=activity_config,
            include_audio=include_audio,
            illustration_style=illustration_style,
            story_type=story_type,
            book_layout=book_layout,
            book_font=book_font,
            # V2 fields
            known_phonemes=known_phonemes,
            focus_phonemes=focus_phonemes,
            sight_words=sight_words,
            strict_decodable=strict_decodable,
            vocabulary_mode=vocabulary_mode,
            focus_mode=focus_mode,
            morphology_focus=morphology_focus,
            story_format=story_format,
            student_age=student_age,
            curriculum=curriculum,
            highlight_text=highlight_text,
            series_info=series_info,
            character_pronouns=character_pronouns,
            reference_character_description=reference_character_description,
            reference_seed=reference_seed,
        )
        pdf_url = result_data.get("pdf_url")
        thumbnail_url = result_data.get("thumbnail_url")
        audio_manifest = result_data.get("audio_manifest")
        worksheets_url = result_data.get("worksheets_url")
        book_only_url = result_data.get("book_only_url")
        pptx_url = result_data.get("pptx_url")

        logger.info(f"Job {job.get('id')} (task {task_id}) completed. PDF URL: {pdf_url}, Thumbnail URL: {thumbnail_url}")
        return {
            "pdf_url": pdf_url,
            "thumbnail_url": thumbnail_url,
            "worksheets_url": worksheets_url,
            "book_only_url": book_only_url,
            "pptx_url": pptx_url,
            "task_id": task_id,
            "audio_manifest": audio_manifest,
        }
    except Exception as e:
        logger.error(f"Job {job['id']} (task {task_id}) failed: {str(e)}")
        error_service.log_error(
            e, context=f"RunPod job {job.get('id')}, task {task_id}"
        )
        # The error is already logged by generate_story_task and DB status updated
        # Return a user-friendly error
        return {
            "error": f"Story generation failed: {str(e)}",
            "task_id": task_id,
            "status_code": 500,
        }


# RunPod handler
async def handler(job: Dict[str, Any]) -> Dict[str, Any]:
    return await process_job(job)


if __name__ == "__main__":
    # This will start the serverless worker for local testing if runpod.serve is called.
    # For actual deployment, RunPod calls the handler function.
    runpod.serverless.start({"handler": handler})
