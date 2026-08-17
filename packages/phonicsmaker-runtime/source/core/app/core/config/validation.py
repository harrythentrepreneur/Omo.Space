# core/config/validation.py

import os
import sys
from typing import Optional
from urllib.parse import urlparse
from app.core.config.logger import logger


def load_and_validate_config():
    """
    Load configuration early and validate critical settings.
    Fail fast if essential configuration is missing.
    """
    from dotenv import load_dotenv
    
    # Load environment variables early - try multiple files
    load_dotenv(".env")
    load_dotenv(".env.development", override=False)
    load_dotenv(".env.local", override=False)
    
    # Set default values for Docker environment
    if not os.getenv("LOCAL_MODE"):
        os.environ["LOCAL_MODE"] = "true"
    
    if not os.getenv("JOB_DONE_URL"):
        os.environ["JOB_DONE_URL"] = "http://localhost:3000/api/job-done"
    
    # Validate JOB_DONE_URL if not in local mode
    local_mode = os.getenv("LOCAL_MODE", "true").lower() == "true"
    job_done_url = os.getenv("JOB_DONE_URL")
    
    if not local_mode and not job_done_url:
        logger.error("JOB_DONE_URL is required when not in LOCAL_MODE")
        sys.exit(1)
    
    if job_done_url and job_done_url != "JOB_DONE_URL":  # Check for placeholder value
        if not validate_url(job_done_url):
            logger.warning(f"Invalid JOB_DONE_URL format: {job_done_url} - continuing in local mode")
            os.environ["LOCAL_MODE"] = "true"
        else:
            logger.info(f"JOB_DONE_URL validated: {job_done_url}")
    elif not local_mode:
        logger.warning("JOB_DONE_URL appears to be a placeholder value - enabling local mode")
        os.environ["LOCAL_MODE"] = "true"
    
    if local_mode:
        logger.info("Running in LOCAL_MODE - callbacks and email disabled")


def validate_url(url: str) -> bool:
    """
    Validate that a URL is properly formatted.
    """
    try:
        parsed = urlparse(url)
        return parsed.scheme in ('http', 'https') and parsed.netloc
    except Exception:
        return False


def build_callback_url(base_url: str, task_id: str, is_stream: bool = False) -> str:
    """
    Build a properly encoded callback URL with query parameters.
    """
    from urllib.parse import urlencode, urljoin
    
    params = {
        'task_id': task_id,
        'isStream': str(is_stream).lower()
    }
    query_string = urlencode(params)
    return f"{base_url}?{query_string}"