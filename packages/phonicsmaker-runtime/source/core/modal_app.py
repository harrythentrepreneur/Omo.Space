"""
Modal serverless app for PhonicsMaker book generation.

Deploy (prod):  modal deploy modal_app.py
Deploy (dev):   DEPLOY_ENV=dev modal deploy modal_app.py
Test:           modal run modal_app.py
"""

import modal
import os

# ─── Environment-aware configuration ─────────────────────────────
# DEPLOY_ENV is read at *deploy time* to select app name, secrets, etc.
# Set DEPLOY_ENV=dev for the dev deployment, defaults to production.
DEPLOY_ENV = os.getenv("DEPLOY_ENV", "production")

if DEPLOY_ENV == "dev":
    APP_NAME = "phonicsmaker-core-dev"
    SECRET_NAME = "phonicsmaker-dev-secrets"
    CONTAINER_ENV = "staging"
else:
    APP_NAME = "phonicsmaker-core"
    SECRET_NAME = "phonicsmaker-secrets"
    CONTAINER_ENV = "production"

# ─── Modal App & Image ────────────────────────────────────────────
app = modal.App(APP_NAME)

# Build identical environment to the RunPod Dockerfile
phonicsmaker_image = (
    modal.Image.debian_slim(python_version="3.12")
    .apt_install(
        "gcc",
        "ffmpeg",
        "curl",
        "build-essential",
        "libpq-dev",
        "libpango-1.0-0",
        "libpangocairo-1.0-0",
        "libpangoft2-1.0-0",
        "libcairo2",
        "libcairo2-dev",
        "libgdk-pixbuf-2.0-0",
        "libffi-dev",
        "libglib2.0-0",
        "libgl1",
        "libglib2.0-dev",
        "shared-mime-info",
        "fonts-dejavu-core",
        "fontconfig",
    )
    .env({
        "PYTHONPATH": "/app",
        "PYTHONUNBUFFERED": "1",
        "ENVIRONMENT": CONTAINER_ENV,
        "OPENBLAS_NUM_THREADS": "1",
        "OMP_NUM_THREADS": "1",
        "MKL_NUM_THREADS": "1",
    })
    .pip_install(
        "poetry",
    )
    # Copy project files into the image
    .add_local_file("pyproject.toml", "/app/pyproject.toml", copy=True)
    .add_local_file("poetry.lock", "/app/poetry.lock", copy=True)
    .run_commands(
        "cd /app && poetry config virtualenvs.create false && poetry install --no-interaction --no-ansi --no-root --only main",
    )
    .add_local_dir("app", "/app/app", copy=True)
    .add_local_dir("templates", "/app/templates", copy=True)
    .add_local_dir("static", "/app/static", copy=True)
    # Install custom fonts
    .run_commands(
        "mkdir -p /usr/share/fonts/truetype/phonicsmaker",
        "cp /app/static/fonts/*.ttf /usr/share/fonts/truetype/phonicsmaker/ 2>/dev/null || true",
        "fc-cache -f",
    )
)


# ─── Background worker function ──────────────────────────────────
# This runs the actual generation in the background, called via .spawn()
@app.function(
    image=phonicsmaker_image,
    timeout=600,  # 10 minutes, same as RunPod config
    secrets=[modal.Secret.from_name(SECRET_NAME)],
    cpu=4.0,
    memory=4096,  # 4 GB RAM
)
async def run_generation(task_id: str, payload: dict, draft_only: bool = False):
    """
    Background worker that generates the book.
    Called via .spawn() from the web endpoint so the HTTP response returns immediately.
    """
    import sys
    import traceback

    # Ensure /app is on path
    sys.path.insert(0, "/app")

    # Load config
    from app.core.config.validation import load_and_validate_config
    load_and_validate_config()

    from app.core.config.logger import logger
    from app.core.config.config import settings
    from app.phonics_maker.tasks.story_tasks import generate_story_task
    from app.phonics_maker.task_management.task_service import TaskService
    from app.phonics_maker.story_generation.story_service import StoryService
    from app.phonics_maker.image_generation.image_service import ImageService
    from app.core.callbacks.callback_service import callback_service
    from app.core.error_handling.error_service import error_service
    from app.db.database import session_scope
    from app.core.user.user_service import UserService

    # Extract fields from payload (same as runpod_handler.py)
    phonemes = payload.get("phonemes")
    story_idea = payload.get("story_idea")
    difficulty_level = payload.get("difficulty_level")
    is_free = payload.get("is_free", False)
    user_email = payload.get("user_email")
    language_variant = payload.get("language_variant")
    debug_config = payload.get("debug_config")

    # Activity configuration
    include_activities = payload.get("include_activities", False)
    activity_config_input = payload.get("activity_config")
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

    # Audio (disabled same as RunPod)
    include_audio = False

    # Book customisation
    illustration_style = payload.get("illustration_style")
    story_type = payload.get("story_type")
    book_layout = payload.get("book_layout")
    book_font = payload.get("book_font")

    # V2 fields
    known_phonemes = payload.get("known_phonemes")
    focus_phonemes = payload.get("focus_phonemes")
    sight_words = payload.get("sight_words")
    strict_decodable = payload.get("strict_decodable")
    vocabulary_mode = payload.get("vocabulary_mode")
    focus_mode = payload.get("focus_mode")
    morphology_focus = payload.get("morphology_focus")
    story_format = payload.get("story_format")
    student_age = payload.get("student_age")
    year_level = payload.get("year_level")
    curriculum = payload.get("curriculum")
    highlight_text = payload.get("highlight_text")
    series_info = payload.get("series_info")
    book_title = payload.get("book_title")
    series_characters = payload.get("series_characters")
    series_theme = payload.get("series_theme")
    character_pronouns = payload.get("character_pronouns")
    page_count = payload.get("page_count")

    # Reference-book fields (reuse a past book's characters/style)
    reference_task_id = payload.get("reference_task_id")
    reference_character_description = payload.get("reference_character_description")
    reference_seed = payload.get("reference_seed")

    logger.info(f"[MODAL] Starting job task_id={task_id}, book_layout={book_layout!r}, book_font={book_font!r}")

    # Look up user DB ID from email
    user_db_id = None
    if user_email:
        try:
            with session_scope() as db:
                user_svc = UserService(db)
                user_db_id = await user_svc.get_user_id_by_email(user_email)
        except ValueError:
            logger.info(f"User {user_email} not found, proceeding without user_db_id")
        except Exception as e:
            logger.error(f"Error fetching user_id for {user_email}: {e}")

    # Create initial DB task record
    task_service = TaskService()

    if reference_task_id and not reference_character_description:
        ref_desc, ref_seed = task_service.get_reference_book_fields(reference_task_id, user_email)
        reference_character_description = ref_desc
        reference_seed = reference_seed if reference_seed is not None else ref_seed

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
            curriculum=curriculum,
            story_type=story_type,
            year_level=year_level,
        )
    except Exception as e:
        logger.error(f"Failed to create task record for {task_id}: {e}")

    # Run generation
    story_service_instance = StoryService()
    image_service_instance = ImageService()
    job = None  # Disable runpod.serverless callbacks in Modal environment

    try:
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
            highlight_text=highlight_text,
            series_info=series_info,
            book_title=book_title,
            series_characters=series_characters,
            series_theme=series_theme,
            draft_only=draft_only,
            character_pronouns=character_pronouns,
            page_count=page_count,
            reference_character_description=reference_character_description,
            reference_seed=reference_seed,
        )

        # If draft_only is true, the response is just the draft JSON and 
        # send_draft_completion was already called inside generate_story_task
        if draft_only:
            logger.info(f"[MODAL] Job {task_id} completed (Draft Mode).")
            return
        pdf_url = result_data.get("pdf_url")
        thumbnail_url = result_data.get("thumbnail_url")
        worksheets_url = result_data.get("worksheets_url")
        book_only_url = result_data.get("book_only_url")
        pptx_url = result_data.get("pptx_url")
        homework_url = result_data.get("homework_url")
        answer_key_url = result_data.get("answer_key_url")
        pdf_compressed_url = result_data.get("pdf_compressed_url")
        variations = result_data.get("variations")
        draft_data_res = result_data.get("draft_data")
        if not draft_data_res and not draft_only:
            draft_data_res = result_data

        logger.info(f"[MODAL] Job {task_id} completed. PDF: {pdf_url}")

        # Send completion callback to /api/job-done
        await callback_service.send_completion(
            task_id=task_id,
            pdf_url=pdf_url,
            thumbnail_url=thumbnail_url,
            worksheets_url=worksheets_url,
            book_only_url=book_only_url,
            homework_url=homework_url,
            answer_key_url=answer_key_url,
            pptx_url=pptx_url,
            pdf_compressed_url=pdf_compressed_url,
            variations=variations,
            draft_data=draft_data_res,
        )

    except Exception as e:
        logger.error(f"[MODAL] Job {task_id} failed: {e}")
        error_service.log_error(e, context=f"Modal job, task {task_id}")

        # Send error callback
        await callback_service.send_error(task_id=task_id, error_message=str(e))


# ─── Web endpoint (returns immediately) ──────────────────────────
@app.function(
    image=phonicsmaker_image,
    secrets=[modal.Secret.from_name(SECRET_NAME)],
)
@modal.fastapi_endpoint(method="POST")
async def generate(payload: dict):
    """
    HTTP endpoint for book generation.
    Returns the task_id immediately and spawns background generation.
    This mirrors RunPod's async behavior.
    """
    import uuid



    # Generate a unique task ID
    task_id = str(uuid.uuid4())

    # Validate required fields
    phonemes = payload.get("phonemes")
    story_idea = payload.get("story_idea")
    difficulty_level = payload.get("difficulty_level")

    if not all([phonemes, story_idea, difficulty_level]):
        return {"error": "Missing required fields", "status_code": 400}

    # Spawn the background worker — this returns immediately
    await run_generation.spawn.aio(task_id=task_id, payload=payload, draft_only=False)

    # Return task_id right away so the frontend can redirect to the loading page
    return {
        "id": task_id,
        "status": "processing",
    }


# ─── Web endpoint (Drafting) ─────────────────────────────────────
@app.function(
    image=phonicsmaker_image,
    secrets=[modal.Secret.from_name(SECRET_NAME)],
)
@modal.fastapi_endpoint(method="POST")
async def generate_draft(payload: dict):
    """
    HTTP endpoint for book draft generation.
    Returns the task_id immediately and spawns background generation.
    """
    import uuid

    # Generate a unique task ID
    task_id = str(uuid.uuid4())

    # Validate required fields
    phonemes = payload.get("phonemes")
    story_idea = payload.get("story_idea")
    difficulty_level = payload.get("difficulty_level")

    if not all([phonemes, story_idea, difficulty_level]):
        return {"error": "Missing required fields", "status_code": 400}

    # Spawn the background worker — this returns immediately
    await run_generation.spawn.aio(task_id=task_id, payload=payload, draft_only=True)

    # Return task_id right away so the frontend can monitor the draft status
    return {
        "id": task_id,
        "status": "drafting",
    }


# ─── Background worker for Finalizing PDF ────────────────────────
@app.function(
    image=phonicsmaker_image,
    timeout=300,  # 5 minutes should be plenty for just PDF generation
    secrets=[modal.Secret.from_name(SECRET_NAME)],
    cpu=4.0,
    memory=4096,  # 4 GB RAM
)
async def run_render_pdf(task_id: str, payload: dict):
    """
    Background worker that takes a finalized draft payload and generates the PDF.
    """
    import sys
    # Ensure /app is on path
    sys.path.insert(0, "/app")

    from app.core.config.validation import load_and_validate_config
    load_and_validate_config()

    from app.core.config.logger import logger
    from app.core.callbacks.callback_service import callback_service
    from app.core.error_handling.error_service import error_service
    from app.phonics_maker.tasks.render_tasks import render_draft_task
    
    logger.info(f"[MODAL] Starting PDF render job task_id={task_id}")
    
    try:
        # We need a new task to handle only the PDF generation side
        # Let's call it render_draft_task
        await render_draft_task(task_id=task_id, payload=payload)
    except Exception as e:
        logger.error(f"[MODAL] PDF Render Job {task_id} failed: {e}")
        error_service.log_error(e, context=f"Modal render job, task {task_id}")
        await callback_service.send_error(task_id=task_id, error_message=str(e))


# ─── Web endpoint (Rendering/Publishing) ──────────────────────────
@app.function(
    image=phonicsmaker_image,
    secrets=[modal.Secret.from_name(SECRET_NAME)],
)
@modal.fastapi_endpoint(method="POST")
async def render_pdf(payload: dict):
    """
    HTTP endpoint for baking a finalized draft into a PDF.
    Receives the full Draft JSON, returns task_id immediately.
    """
    import uuid

    # Use the provided task ID or generate a new one
    task_id = payload.get("task_id") or str(uuid.uuid4())
    payload["task_id"] = task_id  # ensure payload has task_id

    # Validate minimally that we have scenes
    if not payload.get("scenes"):
        return {"error": "Missing scenes in draft payload", "status_code": 400}

    # Spawn the background PDF worker
    await run_render_pdf.spawn.aio(task_id=task_id, payload=payload)

    return {
        "id": task_id,
        "status": "rendering",
    }


# ─── Background worker for Refine Image ──────────────────────────
@app.function(
    image=phonicsmaker_image,
    timeout=600,
    secrets=[modal.Secret.from_name(SECRET_NAME)],
    cpu=4.0,
    memory=4096,
)
async def run_refine_image(task_id: str, scene_number: int, user_request: str):
    """
    Background worker that fetches current task draft data, modifies the prompt for the specified
    scene_number, updates the DB/metadata, and triggers render_draft_task.
    """
    import sys
    sys.path.insert(0, "/app")
    
    from app.core.config.validation import load_and_validate_config
    load_and_validate_config()
    
    from app.core.config.logger import logger
    from app.db.database import session_scope
    from app.db.models.basic import UserGeneration
    from app.core.callbacks.callback_service import callback_service
    from app.core.error_handling.error_service import error_service
    from app.phonics_maker.tasks.render_tasks import render_draft_task
    from app.phonics_maker.image_generation.image_service import _CHANGE_MARKER
    
    logger.info(f"[MODAL] Starting image refinement job task_id={task_id}, scene={scene_number}")
    
    try:
        draft_payload = None
        with session_scope() as session:
            generation = session.query(UserGeneration).filter(UserGeneration.task_id == task_id).first()
            if not generation:
                raise ValueError(f"Task {task_id} not found in database")
            
            task_meta = generation.task_metadata
            if isinstance(task_meta, str):
                import json
                task_meta = json.loads(task_meta)
            
            draft_payload = task_meta.get("draft_data")
            
        if not draft_payload:
            raise ValueError(f"No draft data found for task {task_id}")
            
        # Modify the prompt at scene_number
        images = draft_payload.get("images", [])
        if scene_number < 0 or scene_number >= len(images):
            raise ValueError(f"Scene number {scene_number} out of bounds (0-{len(images)-1})")
            
        target_image = images[scene_number]
        original_prompt = target_image.get("prompt", "")
        
        # Split prompt at existing change marker if any, to keep it clean
        if _CHANGE_MARKER in original_prompt:
            original_prompt = original_prompt.split(_CHANGE_MARKER, 1)[0].strip()
            
        new_prompt = f"{original_prompt}\n\n{_CHANGE_MARKER}{user_request}"
        target_image["prompt"] = new_prompt
        
        # Save the updated draft data back to the database
        from app.phonics_maker.task_management.task_service import TaskService
        ts = TaskService()
        ts.update_task_intermediate(task_id, {"draft_data": draft_payload})
        
        # Run render draft task with the updated payload and regenerate_image_indices
        render_payload = {
            **draft_payload,
            "task_id": task_id,
            "regenerate_image_indices": [scene_number]
        }
        
        await render_draft_task(task_id=task_id, payload=render_payload)
        
    except Exception as e:
        logger.error(f"[MODAL] Image refinement failed for task {task_id}: {e}")
        error_service.log_error(e, context=f"Modal image refinement, task {task_id}")
        await callback_service.send_error(task_id=task_id, error_message=str(e))


@app.function(
    image=phonicsmaker_image,
    secrets=[modal.Secret.from_name(SECRET_NAME)],
)
@modal.fastapi_endpoint(method="POST")
async def refine_image(payload: dict):
    """
    HTTP endpoint for starting an image refinement task.
    Receives taskId, scene_number, user_request in body.
    """
    import uuid
    from app.core.config.logger import logger

    task_id = payload.get("task_id") or str(uuid.uuid4())
    scene_number = payload.get("scene_number")
    user_request = payload.get("user_request")

    if not task_id or scene_number is None or user_request is None:
        return {"error": "Missing required fields", "status_code": 400}

    # Spawn the background worker
    await run_refine_image.spawn.aio(task_id=task_id, scene_number=int(scene_number), user_request=user_request)

    return {
        "id": task_id,
        "status": "rendering",
    }
