# phonics_maker/task_management/task_service.py

from typing import Optional, List, Tuple, Union, Dict, Any
from datetime import datetime
from pathlib import Path
from uuid import UUID
from app.core.config.logger import logger, set_task_id
from app.db.database import session_scope
from app.db.models.basic import UserGeneration, User
from app.db.models.task import TaskStatus
from app.db.models.story import LanguageVariant
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm.attributes import flag_modified
import json


class TaskService:
    def __init__(self):
        self.namespace = "task_db"  # Or remove if not used
        # self.user_email = None # Can be passed per method or set per invocation

    def _get_base_task_id(self, task_id: str) -> str:
        """
        Helper method to get the base UUID part from a task ID that might have a suffix.
        Validates if the task_id is a valid UUID before processing.
        Now, this might be less relevant if task_id is just a string, but keeping if 
        suffixes are still used or if validation is desired.
        """
        # If task_id is just a string and not necessarily UUID, this validation might change or be removed.
        # For now, assuming it might still contain UUID-like structures or suffixes.
        try:
            UUID(task_id) # Try to parse as UUID
            return task_id
        except ValueError:
            parts = task_id.split("-")
            if len(parts) >= 5:
                base_id = "-".join(parts[:5])
                try:
                    UUID(base_id)
                    return base_id
                except ValueError:
                    # If it's not a UUID and we're okay with arbitrary strings,
                    # just return the original task_id or handle as per new rules.
                    # For now, we'll assume it should at least look like one if it has hyphens.
                    logger.warning(f"Task ID {task_id} has hyphens but is not a valid UUID structure. Using as is.")
                    return task_id # Or raise error if strict format is needed
            else:
                # If no hyphens or not UUID-like, assume it's a valid string ID
                return task_id


    def create_task_record(
        self,
        task_id: str,
        user_id: Optional[str],  # Clerk/DB user ID (which is a UUID in User table)
        phonemes: List[str],
        story_idea: str,
        difficulty_level: str,
        is_free: bool,
        user_email: Optional[str] = None,
        language_variant: Optional[LanguageVariant] = None, # This is passed as string from handler
        curriculum: Optional[str] = None,
        story_type: Optional[str] = None,
        year_level: Optional[str] = None,
    ) -> str:
        """
        Create or update (upsert) a task record in the database.
        The frontend already creates this row when submitting to RunPod, so on
        conflict we just move the status to PROCESSING and refresh updated_at.
        """
        logger.info(f"Upserting task record for {task_id}")
        with session_scope() as session:
            try:
                now = datetime.now()
                set_task_id(task_id)

                # Ensure user_id is UUID if provided
                db_user_id = None
                if user_id:
                    try:
                        db_user_id = UUID(user_id)
                    except ValueError:
                        logger.error(f"Invalid user_id format: {user_id}. Must be a UUID.")
                        raise ValueError(f"Invalid user_id format: {user_id}")


                metadata = {
                    "phonemes": phonemes,
                    "story_idea": story_idea,
                    "difficulty_level": difficulty_level,
                    "is_free": is_free,
                    "language_variant": language_variant.value if isinstance(language_variant, LanguageVariant) else language_variant,
                    "curriculum": curriculum,
                    "story_type": story_type,
                    "year_level": year_level,
                }

                stmt = pg_insert(UserGeneration).values(
                    task_id=task_id,
                    user_id=db_user_id,
                    email=user_email,
                    task_metadata=json.dumps(metadata),
                    status=TaskStatus.PROCESSING.value,
                    created_at=now,
                    updated_at=now,
                ).on_conflict_do_update(
                    index_elements=["task_id"],
                    set_={
                        "status": TaskStatus.PROCESSING.value,
                        "updated_at": now,
                    },
                )
                session.execute(stmt)
                session.flush()
                logger.info(f"Upserted task DB record {task_id} for user {user_email}")
                return task_id
            except Exception as e:
                logger.error(f"Error upserting task DB record {task_id}: {str(e)}")
                raise e

    def set_task_result(
        self,
        task_id: str,
        pdf_url: Optional[str] = None,
        thumbnail_url: Optional[str] = None,
        current_user_email: Optional[str] = None,
        status: Union[TaskStatus, str] = TaskStatus.COMPLETED,
        error_message: Optional[str] = None,
        metadata_update: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Set the final result (PDF URL, thumbnail URL) and status for a task in the database.
        """
        with session_scope() as session:
            try:
                # task_id is now a string, directly query with it
                generation = (
                    session.query(UserGeneration)
                    .filter(UserGeneration.task_id == task_id)
                    .with_for_update()
                    .first()
                )
                if not generation:
                    logger.warning(
                        f"Task DB record {task_id} not found for setting result."
                    )
                    return

                # Map TaskStatus to lowercase strings for DB schema consistency
                if isinstance(status, TaskStatus):
                    if status == TaskStatus.COMPLETED:
                        db_status = "completed"
                    elif status == TaskStatus.FAILED:
                        db_status = "failed"
                    elif status == TaskStatus.DRAFT_READY:
                        db_status = "draft_ready"
                    else:
                        db_status = status.value.lower()
                else:
                    db_status = str(status).lower()

                generation.status = db_status
                if pdf_url:
                    generation.result_url = pdf_url
                if thumbnail_url:
                    generation.thumbnail_url = thumbnail_url
                generation.updated_at = datetime.now()
                
                if current_user_email and not generation.email:
                    generation.email = current_user_email
                
                task_meta = generation.task_metadata
                if isinstance(task_meta, str):
                    try:
                        task_meta = json.loads(task_meta)
                    except Exception:
                        task_meta = {}
                elif not isinstance(task_meta, dict):
                    task_meta = {}

                if error_message:
                    task_meta["error_message"] = error_message

                if metadata_update:
                    filtered_update = {k: v for k, v in metadata_update.items() if v is not None}
                    task_meta.update(filtered_update)

                generation.task_metadata = task_meta
                flag_modified(generation, "task_metadata")

                session.add(generation)
                logger.info(f"Set task DB record {task_id} result. PDF: {pdf_url}, Thumbnail: {thumbnail_url}, Status: {db_status}")
            except Exception as e:
                logger.error(f"Error setting task DB record result {task_id}: {str(e)}")

    def get_reference_book_fields(
        self, reference_task_id: str, owner_email: Optional[str] = None
    ) -> Tuple[Optional[str], Optional[int]]:
        """
        Resolve a past book's character_description and book_seed so a new book
        can reuse them. Reads UserGeneration.task_metadata.draft_data first,
        falling back to draft_data/{task_id}.json on disk (local dev).
        The DB lookup is scoped to owner_email so a caller can only reference
        their own books. Returns (None, None) on any failure so generation
        degrades gracefully.
        """
        draft_data = None
        try:
            with session_scope() as session:
                generation = None
                if owner_email:
                    generation = (
                        session.query(UserGeneration)
                        .filter(
                            UserGeneration.task_id == reference_task_id,
                            UserGeneration.email == owner_email,
                        )
                        .first()
                    )
                if generation:
                    task_meta = generation.task_metadata
                    if isinstance(task_meta, str):
                        try:
                            task_meta = json.loads(task_meta)
                        except Exception:
                            task_meta = {}
                    if isinstance(task_meta, dict):
                        candidate = task_meta.get("draft_data")
                        if isinstance(candidate, dict):
                            draft_data = candidate
        except Exception as e:
            logger.warning(f"Failed to load reference book {reference_task_id} from DB: {e}")

        if draft_data is None:
            try:
                draft_filepath = (
                    Path(__file__).resolve().parent.parent.parent.parent
                    / "draft_data"
                    / f"{reference_task_id}.json"
                )
                if draft_filepath.exists():
                    with open(draft_filepath) as f:
                        candidate = json.load(f)
                    if isinstance(candidate, dict):
                        draft_data = candidate
            except Exception as e:
                logger.warning(f"Failed to load reference book {reference_task_id} from disk: {e}")

        if not draft_data:
            logger.warning(f"Reference book {reference_task_id} has no usable draft data")
            return None, None

        character_description = draft_data.get("character_description") or None
        seed = None
        try:
            raw_seed = draft_data.get("book_seed")
            if raw_seed is not None:
                seed = int(raw_seed)
        except (TypeError, ValueError):
            logger.warning(f"Reference book {reference_task_id} has non-numeric book_seed")

        if character_description or seed is not None:
            logger.info(
                f"Resolved reference book {reference_task_id}: "
                f"character_description={'yes' if character_description else 'no'}, seed={seed}"
            )
        return character_description, seed

    async def get_user_name(
        self, user_email: str
    ) -> str:
        if not user_email:
            return "there"

        with session_scope() as session:
            try:
                user = session.query(User).filter(User.email == user_email).first()
                if user and user.full_name:
                    first_name = user.full_name.split(" ")[0]
                    return first_name
                name_from_email = user_email.split("@")[0]
                return name_from_email
            except Exception as e:
                logger.error(
                    f"Error getting user name for email {user_email}: {str(e)}"
                )
                return "there"

    async def set_user_email_for_task(self, task_id: str, email: str) -> None:
        logger.info(f"Setting user email for task {task_id}")
        with session_scope() as session:
            try:
                # task_id is now a string, directly query with it
                generation = (
                    session.query(UserGeneration)
                    .filter(UserGeneration.task_id == task_id)
                    .first()
                )
                if generation and not generation.email:
                    generation.email = email
                    generation.updated_at = datetime.now()
                    session.add(generation)
                    logger.info(
                        f"Associated email {email} with task DB record {task_id}"
                    )
                elif generation and generation.email and generation.email != email:
                    logger.warning(
                        f"Task {task_id} already has email {generation.email}, not overwriting with {email}"
                    )
                elif not generation:
                    logger.warning(f"Task DB record {task_id} not found to set email.")
            except Exception as e:
                logger.error(
                    f"Error setting user email for task DB record {task_id}: {str(e)}"
                )

    def update_task_progress(
        self,
        task_id: str,
        progress: int,
        message: Optional[str] = None
    ) -> None:
        """
        Update task progress and message directly in the database.
        """
        with session_scope() as session:
            try:
                generation = (
                    session.query(UserGeneration)
                    .filter(UserGeneration.task_id == task_id)
                    .with_for_update()
                    .first()
                )
                if not generation:
                    logger.warning(
                        f"Task DB record {task_id} not found for setting progress."
                    )
                    return

                # Guard: Do not downgrade a terminal status (completed, failed, draft_ready)
                current_status = (generation.status or "").lower()
                if current_status in ["completed", "failed", "draft_ready"]:
                    logger.warning(
                        f"Skipping progress update to {progress}% for {task_id}: task is already in terminal state '{current_status}'"
                    )
                    return

                generation.status = "processing"
                generation.updated_at = datetime.now()

                # Get existing metadata
                task_meta = generation.task_metadata
                if isinstance(task_meta, str):
                    try:
                        task_meta = json.loads(task_meta)
                    except Exception:
                        task_meta = {}
                elif not isinstance(task_meta, dict):
                    task_meta = {}

                # Merge progress and message
                task_meta["progress"] = progress
                if message:
                    task_meta["message"] = message
                task_meta["lastUpdated"] = datetime.now().isoformat()

                generation.task_metadata = task_meta
                flag_modified(generation, "task_metadata")
                session.add(generation)
                logger.info(f"Direct DB progress update for task {task_id}: {progress}% - {message}")
            except Exception as e:
                logger.error(f"Error updating task DB progress {task_id}: {str(e)}")

    def update_task_intermediate(
        self,
        task_id: str,
        data: dict
    ) -> None:
        """
        Update intermediate generation data (phase, cover, title, etc.) directly in the database.
        """
        with session_scope() as session:
            try:
                generation = (
                    session.query(UserGeneration)
                    .filter(UserGeneration.task_id == task_id)
                    .with_for_update()
                    .first()
                )
                if not generation:
                    logger.warning(
                        f"Task DB record {task_id} not found for intermediate update."
                    )
                    return

                # Guard: Do not downgrade a terminal status (completed, failed, draft_ready)
                current_status = (generation.status or "").lower()
                if current_status in ["completed", "failed", "draft_ready"]:
                    logger.warning(
                        f"Skipping intermediate update for {task_id}: task is already in terminal state '{current_status}'"
                    )
                    return

                generation.status = "processing"
                generation.updated_at = datetime.now()

                # Get existing metadata
                task_meta = generation.task_metadata
                if isinstance(task_meta, str):
                    try:
                        task_meta = json.loads(task_meta)
                    except Exception:
                        task_meta = {}
                elif not isinstance(task_meta, dict):
                    task_meta = {}

                # Merge intermediate data
                task_meta.update(data)
                task_meta["lastUpdated"] = datetime.now().isoformat()

                generation.task_metadata = task_meta
                flag_modified(generation, "task_metadata")
                session.add(generation)
                logger.info(f"Direct DB intermediate update for task {task_id}: keys={list(data.keys())}")
            except Exception as e:
                logger.error(f"Error updating task DB intermediate data {task_id}: {str(e)}")