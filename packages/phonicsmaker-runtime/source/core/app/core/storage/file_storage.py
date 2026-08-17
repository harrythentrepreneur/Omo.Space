# core/storage/file_storage.py

import os
import asyncio
import functools
import threading
import boto3
import boto3.exceptions
from botocore.client import Config

from app.core.config.config import settings
from app.core.config.logger import logger
from app.core.utils.retry import retry

class StorageError(Exception):
    """Custom exception for storage-related errors"""
    pass


# ── Lazy singleton S3 client (avoids re-creating per upload) ───────
_spaces_client = None
_client_lock = threading.Lock()


def _get_spaces_client():
    """Return a reusable S3 client, creating it once on first call."""
    global _spaces_client
    if _spaces_client is None:
        with _client_lock:
            if _spaces_client is None:
                session = boto3.session.Session()
                _spaces_client = session.client(
                    "s3",
                    region_name=settings.SPACES_REGION,
                    endpoint_url=f"https://{settings.SPACES_ENDPOINT}",
                    aws_access_key_id=settings.SPACES_KEY,
                    aws_secret_access_key=settings.SPACES_SECRET,
                    config=Config(signature_version="s3v4"),
                )
    return _spaces_client


@retry(
    exceptions=(boto3.exceptions.Boto3Error,),
    max_retries=settings.STORAGE_MAX_RETRIES,
    initial_delay=settings.STORAGE_RETRY_DELAY,
    max_delay=settings.STORAGE_RETRY_DELAY * 4,
    backoff_factor=2.0,
    log_retries=True
)
async def upload_result(file_path: str, task_id: str) -> str:
    """
    Upload a file to DigitalOcean Spaces with retry mechanism.
    
    Args:
        file_path: Local path to the file to upload
        task_id: Task ID used for organizing files in storage
        
    Returns:
        str: Public URL of the uploaded file
        
    Raises:
        StorageError: If upload fails after all retries
    """
    try:
        # Validate file exists before attempting upload
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        logger.info(f"Attempting to upload file to DigitalOcean Spaces: {file_path}")

        spaces_client = _get_spaces_client()

        bucket_name = settings.SPACES_NAME
        object_name = f"generated_pdfs/{task_id}/{os.path.basename(file_path)}"

        # Determine content type from file extension
        content_type_map = {
            '.pdf': 'application/pdf',
            '.pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
        }
        ext = os.path.splitext(file_path)[1].lower()
        content_type = content_type_map.get(ext, 'application/octet-stream')

        # Run the blocking boto3 upload in a thread pool so asyncio.gather
        # can truly parallelise multiple uploads at the same time.
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(
            None,  # default ThreadPoolExecutor
            functools.partial(
                spaces_client.upload_file,
                file_path,
                bucket_name,
                object_name,
                ExtraArgs={
                    "ACL": "public-read",
                    "ContentType": content_type
                },
            ),
        )

        # Use CDN endpoint for public URLs when available, fall back to direct endpoint
        cdn_endpoint = settings.SPACES_CDN_ENDPOINT or settings.SPACES_ENDPOINT
        public_url = f"https://{bucket_name}.{cdn_endpoint}/{object_name}"
        logger.info(f"Successfully uploaded file to: {public_url}")
        
        return public_url

    except FileNotFoundError as e:
        logger.error(f"File not found error: {str(e)}")
        raise StorageError(f"File not found: {file_path}") from e
    except boto3.exceptions.S3UploadFailedError as e:
        logger.error(f"S3 upload failed: {str(e)}")
        raise StorageError("Failed to upload file to storage") from e
    except Exception as e:
        logger.error(f"Unexpected error during file upload: {str(e)}")
        raise StorageError("Failed to upload file") from e