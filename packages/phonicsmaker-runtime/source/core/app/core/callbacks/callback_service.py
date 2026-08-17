# core/callbacks/callback_service.py

import asyncio
import json
import time
import random
from typing import Dict, Any, Optional
from urllib.parse import urljoin, urlencode

import httpx
from app.core.config.config import settings
from app.core.config.logger import logger
from app.core.config.validation import build_callback_url, validate_url


class CallbackService:
    """
    Service for handling job callbacks with resilient retry logic.
    """
    
    def __init__(self):
        self.max_retries = 3
        self.base_delay = 1.0  # Base delay in seconds
        self.max_delay = 30.0  # Maximum delay in seconds
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def send_progress(self, task_id: str, progress: int, message: Optional[str] = None) -> bool:
        """
        Send progress update to callback URL.
        
        Args:
            task_id: Unique task identifier
            progress: Progress percentage (0-100)
            message: Optional progress message
            
        Returns:
            True if successful, False otherwise
        """
        # Update progress directly in the database
        try:
            from app.phonics_maker.task_management.task_service import TaskService
            task_svc = TaskService()
            task_svc.update_task_progress(task_id, progress, message)
        except Exception as e:
            logger.error(f"Failed to write progress directly to DB for {task_id}: {e}")

        if settings.LOCAL_MODE:
            logger.debug(f"LOCAL_MODE: Skipping progress webhook for task {task_id} - {progress}%")
            return True
            
        if not settings.JOB_DONE_URL:
            logger.warning("No JOB_DONE_URL configured for progress callbacks")
            return False
            
        payload = {
            "task_id": task_id,
            "progress": progress,
            "status": "in_progress",
            "message": message
        }
        
        asyncio.create_task(self._send_callback("progress", payload))
        return True
    
    async def send_completion(self, task_id: str, pdf_url: str, thumbnail_url: str, worksheets_url: str = None, book_only_url: str = None, homework_url: str = None, answer_key_url: str = None, pptx_url: str = None, variations: Optional[Dict[str, str]] = None, draft_data: Optional[Dict[str, Any]] = None, pdf_compressed_url: str = None) -> bool:
        """
        Send completion notification to callback URL.

        Args:
            task_id: Unique task identifier
            pdf_url: URL to generated PDF (combined book + worksheets)
            thumbnail_url: URL to generated thumbnail
            worksheets_url: URL to separate worksheets-only PDF
            homework_url: URL to homework PDF (worksheets without answer key)
            answer_key_url: URL to answer key PDF (teacher copy)
            pptx_url: URL to PowerPoint presentation (for smartboard display)
            variations: Dictionary of variation PDFs mapped by difficulty level
            draft_data: The structured Draft Payload for WYSIWYG editing
            pdf_compressed_url: URL to print-friendly combined PDF (smaller file)

        Returns:
            True if successful, False otherwise
        """
        # Update completion directly in the database
        try:
            from app.phonics_maker.task_management.task_service import TaskService
            from app.db.models.task import TaskStatus
            task_svc = TaskService()
            completion_metadata: Dict[str, Any] = {
                "progress": 100,
                "completedAt": int(time.time() * 1000),
                "message": "Generation completed successfully",
                "worksheets_url": worksheets_url,
                "book_only_url": book_only_url,
                "homework_url": homework_url,
                "answer_key_url": answer_key_url,
                "pptx_url": pptx_url,
                "pdf_compressed_url": pdf_compressed_url,
                "variations": variations,
            }
            if draft_data is not None:
                completion_metadata["draft_data"] = draft_data
            task_svc.set_task_result(
                task_id=task_id,
                pdf_url=pdf_url,
                thumbnail_url=thumbnail_url,
                status=TaskStatus.COMPLETED,
                metadata_update=completion_metadata,
            )
        except Exception as e:
            logger.error(f"Failed to write completion directly to DB for {task_id}: {e}")

        if settings.LOCAL_MODE:
            logger.debug(f"LOCAL_MODE: Skipping completion webhook for task {task_id}")
            return True
            
        if not settings.JOB_DONE_URL:
            logger.warning("No JOB_DONE_URL configured for completion callbacks")
            return False
            
        payload = {
            "task_id": task_id,
            "status": "completed",
            "pdf_url": pdf_url,
            "thumbnail_url": thumbnail_url,
            "completed_at": time.time(),
            # Always include individual URLs (even if None) so the
            # receiving endpoint has the full picture
            "worksheets_url": worksheets_url,
            "book_only_url": book_only_url,
            "homework_url": homework_url,
            "answer_key_url": answer_key_url,
            "pptx_url": pptx_url,
            "pdf_compressed_url": pdf_compressed_url,
            "variations": variations,
            "draft_data": draft_data,
        }
        
        return await self._send_callback("completion", payload)

    async def send_draft_completion(self, task_id: str, draft_data: Dict[str, Any]) -> bool:
        """
        Send a draft completion notification to the callback URL.
        This sends the structured JSON (scenes, images, phonemes, activities) 
        back to the frontend for WYSIWYG editing, without baking a PDF yet.
        """
        # Update draft completion directly in the database
        try:
            from app.phonics_maker.task_management.task_service import TaskService
            from app.db.models.task import TaskStatus
            task_svc = TaskService()
            task_svc.set_task_result(
                task_id=task_id,
                status=TaskStatus.DRAFT_READY,
                metadata_update={
                    "progress": 100,
                    "completedAt": int(time.time() * 1000),
                    "message": "Draft generated successfully",
                    "draft_data": draft_data
                }
            )
        except Exception as e:
            logger.error(f"Failed to write draft completion directly to DB for {task_id}: {e}")

        if settings.LOCAL_MODE:
            logger.debug(f"LOCAL_MODE: Skipping draft webhook for task {task_id}")
            return True
            
        if not settings.JOB_DONE_URL:
            logger.warning("No JOB_DONE_URL configured for draft callbacks")
            return False
            
        payload = {
            "task_id": task_id,
            "status": "draft_ready",
            "completed_at": time.time(),
            "draft_data": draft_data
        }
        
        return await self._send_callback("draft_ready", payload)
    
    async def send_intermediate_data(self, task_id: str, data: Dict[str, Any]) -> bool:
        """
        Send intermediate generation data (story title, cover image, preview images, phase)
        so the frontend can show progressive previews during generation.
        In LOCAL_MODE this is a no-op — the local server monkey-patches this
        to store data in active_tasks directly.
        """
        # Update intermediate data directly in the database
        try:
            from app.phonics_maker.task_management.task_service import TaskService
            task_svc = TaskService()
            task_svc.update_task_intermediate(task_id, data)
        except Exception as e:
            logger.error(f"Failed to write intermediate data directly to DB for {task_id}: {e}")

        if settings.LOCAL_MODE:
            logger.debug(f"LOCAL_MODE: Intermediate data update for {task_id}: phase={data.get('phase')}")
            return True

        if not settings.JOB_DONE_URL:
            logger.warning("No JOB_DONE_URL configured for intermediate data callbacks")
            return False

        payload = {
            "task_id": task_id,
            "status": "in_progress",
            **data,
        }

        asyncio.create_task(self._send_callback("intermediate", payload))
        return True

    async def send_error(self, task_id: str, error_message: str) -> bool:
        """
        Send error notification to callback URL.
        
        Args:
            task_id: Unique task identifier
            error_message: Error description
            
        Returns:
            True if successful, False otherwise
        """
        # Update error directly in the database
        try:
            from app.phonics_maker.task_management.task_service import TaskService
            from app.db.models.task import TaskStatus
            task_svc = TaskService()
            task_svc.set_task_result(
                task_id=task_id,
                status=TaskStatus.FAILED,
                error_message=error_message,
                metadata_update={
                    "progress": 100,
                    "failedAt": int(time.time() * 1000),
                    "message": f"Error: {error_message}"
                }
            )
        except Exception as e:
            logger.error(f"Failed to write error directly to DB for {task_id}: {e}")

        if settings.LOCAL_MODE:
            logger.debug(f"LOCAL_MODE: Skipping error webhook for task {task_id}")
            return True
            
        if not settings.JOB_DONE_URL:
            logger.warning("No JOB_DONE_URL configured for error callbacks")
            return False
            
        payload = {
            "task_id": task_id,
            "status": "failed",
            "error": error_message,
            "failed_at": time.time()
        }
        
        return await self._send_callback("error", payload)
    
    async def _send_callback(self, callback_type: str, payload: Dict[str, Any]) -> bool:
        """
        Send callback with exponential backoff retry logic.
        
        Args:
            callback_type: Type of callback (progress, completion, error)
            payload: Data to send
            
        Returns:
            True if successful, False otherwise
        """
        url = build_callback_url(settings.JOB_DONE_URL, payload.get("task_id", ""), False)
        
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "PhonicsMaker-Callback/1.0"
        }
        if settings.JOB_DONE_SECRET:
            headers["Authorization"] = f"Bearer {settings.JOB_DONE_SECRET}"
            
        for attempt in range(self.max_retries + 1):
            try:
                headers = {
                    "Content-Type": "application/json",
                    "User-Agent": "PhonicsMaker-Callback/1.0",
                }
                if settings.JOB_DONE_SECRET:
                    headers["Authorization"] = f"Bearer {settings.JOB_DONE_SECRET}"
                
                response = await self.client.post(
                    url,
                    json=payload,
                    headers=headers,
                )
                
                if response.status_code < 400:
                    logger.info(f"Callback {callback_type} sent successfully for task {payload.get('task_id')}")
                    return True
                else:
                    logger.warning(
                        f"Callback {callback_type} failed with status {response.status_code} "
                        f"for task {payload.get('task_id')}: {response.text}"
                    )
                    
            except Exception as e:
                logger.error(
                    f"Callback {callback_type} attempt {attempt + 1} failed for "
                    f"task {payload.get('task_id')}: {str(e)}"
                )
            
            # Don't retry on the last attempt
            if attempt < self.max_retries:
                delay = min(
                    self.base_delay * (2 ** attempt) + random.uniform(0, 1),
                    self.max_delay
                )
                logger.info(f"Retrying callback in {delay:.2f} seconds...")
                await asyncio.sleep(delay)
        
        # Log final failure with detailed information
        logger.error(
            f"Failed to send {callback_type} callback after {self.max_retries + 1} attempts. "
            f"URL: {url}, Task: {payload.get('task_id')}, "
            f"Status: {response.status_code if 'response' in locals() else 'No response'}, "
            f"Body: {response.text if 'response' in locals() else 'No response body'}"
        )
        
        return False
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()


# Global callback service instance
callback_service = CallbackService()