# core/config/config.py

import os
from functools import lru_cache
from typing import Optional
from pydantic_settings import BaseSettings


class BaseConfig(BaseSettings):
    # Environment configuration
    ENVIRONMENT: str = "development"
    LOCAL_MODE: bool = False  # Skip callbacks and email in local dev

    BASE_URL: Optional[str] = "http://127.0.0.1:8000"
    
    # Callback configuration for RunPod
    JOB_DONE_URL: Optional[str] = None  # URL for job completion callbacks
    JOB_DONE_SECRET: Optional[str] = None  # Shared secret for callback auth

    # AI configuration
    GEMINI_API_KEY: Optional[str] = None
    RUNWARE_API_KEY: Optional[str] = None

    # Database configuration
    DATABASE_URL: Optional[str] = None

    # Redis configuration
    REDIS_URL: Optional[str] = "redis://localhost:6379/0"

    # Rate limits
    RATE_LIMIT_WINDOW_SECONDS: int = 86400  # 1 day
    RATE_LIMIT_X: int = 1
    RATE_LIMIT_THREADS: int = 1
    RATE_LIMIT_LINKEDIN: int = 1

    # Scheduler configuration
    PRODUCE_INTERVAL_SECONDS: Optional[int] = None
    CONSUME_INTERVAL_SECONDS: Optional[int] = None
    STORY_GENERATION_INTERVAL_SECONDS: Optional[int] = 60  # Default: 60 seconds

    # Email configuration
    RESEND_API_KEY: Optional[str] = None
    EMAIL_SUBJECT: Optional[str] = None
    FROM_EMAIL: Optional[str] = None
    FROM_NAME: Optional[str] = None

    # Clerk
    CLERK_SECRET_KEY: Optional[str] = None

    # Sentry configuration
    SENTRY_DSN: Optional[str] = None

    # API Key
    API_KEY: Optional[str] = None

    # Fish Audio TTS
    FISH_AUDIO_API_KEY: Optional[str] = None
    FISH_AUDIO_MODEL: str = "s1"  # Recommended. Options: s1, speech-1.5, speech-1.6
    FISH_AUDIO_VOICE_ID: Optional[str] = None  # Default / fallback voice reference ID
    # Per-accent English voices
    FISH_AUDIO_VOICE_ID_US: Optional[str] = None  # American English voice
    FISH_AUDIO_VOICE_ID_UK: Optional[str] = None  # British English voice
    FISH_AUDIO_VOICE_ID_AU: Optional[str] = None  # Australian English voice
    FISH_AUDIO_VOICE_ID_NZ: Optional[str] = None  # New Zealand English voice
    FISH_AUDIO_VOICE_ID_CA: Optional[str] = None  # Canadian English voice
    # Non-English languages
    FISH_AUDIO_VOICE_ID_FR: Optional[str] = None  # French voice
    FISH_AUDIO_VOICE_ID_ES: Optional[str] = None  # Spanish voice
    
    # Audio narration
    AUDIO_ENABLED: bool = False  # Master toggle for audio generation
    AUDIO_PUBLIC_BASE_URL: str = "https://phonicsmaker.com"  # For /listen/{bookId} links

    # Storage
    SPACES_REGION: Optional[str] = None
    SPACES_ENDPOINT: Optional[str] = None
    SPACES_KEY: Optional[str] = None
    SPACES_SECRET: Optional[str] = None
    SPACES_NAME: Optional[str] = None
    SPACES_CDN_ENDPOINT: Optional[str] = None  # CDN endpoint for public URLs (falls back to SPACES_ENDPOINT)

    # Retry configuration
    PDF_GENERATION_MAX_RETRIES: int = 2
    PDF_GENERATION_RETRY_DELAY: float = 1.0
    PDF_GENERATION_MAX_DELAY: float = 10.0

    PDF_PROCESS_MAX_RETRIES: int = 3
    PDF_PROCESS_RETRY_DELAY: float = 0.5
    PDF_PROCESS_MAX_DELAY: float = 5.0

    # AI-specific retries
    GEMINI_MAX_RETRIES: int = 3
    GEMINI_RETRY_DELAY: float = 10.0
    GEMINI_MAX_DELAY: float = 60.0

    RUNWARE_MAX_RETRIES: int = 3
    RUNWARE_RETRY_DELAY: float = 1.0
    RUNWARE_MAX_DELAY: float = 15.0

    # Storage-specific retries
    STORAGE_MAX_RETRIES: int = 3
    STORAGE_RETRY_DELAY: float = 3.0

    # Download-specific retries
    DOWNLOAD_IMAGE_MAX_RETRIES: int = 4
    DOWNLOAD_IMAGE_RETRY_DELAY: float = 3.0
    DOWNLOAD_IMAGE_MAX_DELAY: float = 10.0

    # short scenes retries
    GENERATE_SCENES_MAX_RETRIES: int = 4
    GENERATE_SCENES_DELAY: float = 1.0

    # Image generation retries
    IMAGE_PROMPT_GEN_MAX_RETRIES: int = 4
    IMAGE_PROMPT_GEN_RETRY_DELAY: float = 10.0
    IMAGE_PROMPT_GEN_MAX_DELAY: float = 60.0

    # Image validation: max attempts to regenerate when Runware returns corrupt images
    IMAGE_GENERATION_VALIDATION_MAX_ATTEMPTS: int = 5

    # These are needed for systems with GPUs
    OPENBLAS_NUM_THREADS: int = 1
    OMP_NUM_THREADS: int = 1
    MKL_NUM_THREADS: int = 1

    model_config = {
        "env_file_encoding": "utf-8",
        "case_sensitive": True,
        "validate_assignment": True,
    }


class TestConfig(BaseConfig):
    model_config = {
        **BaseConfig.model_config,
        "env_file": ".env.test"
    }


class DevelopmentConfig(BaseConfig):
    model_config = {
        **BaseConfig.model_config,
        "env_file": ".env.development"
    }


class StagingConfig(BaseConfig):
    model_config = {
        **BaseConfig.model_config,
        "env_file": ".env.staging"
    }


class ProductionConfig(BaseConfig):
    model_config = {
        **BaseConfig.model_config,
        "env_file": ".env.production"
    }


@lru_cache()
def get_settings() -> BaseConfig:
    """
    Get configuration based on environment.
    Uses environment variable ENVIRONMENT to determine which configuration to load.
    Caches the result using lru_cache.
    """
    environment = os.getenv("ENVIRONMENT", "development")
    config_by_environment = {
        "test": TestConfig,
        "development": DevelopmentConfig,
        "staging": StagingConfig,
        "production": ProductionConfig,
    }
    config_class = config_by_environment.get(environment, DevelopmentConfig)
    return config_class()


# Create a settings instance
settings = get_settings()
