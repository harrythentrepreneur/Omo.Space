# core/models/story.py

from pydantic import BaseModel
from typing import List, Optional
from enum import Enum

class LanguageVariant(str, Enum):
    US = "US"
    UK = "UK"
    AU = "AU"
    FR = "FR"
    ES = "ES"

class DifficultyLevel(str, Enum):
    # New 1-5 scale (primary keys)
    LEVEL_1 = "1"  # Beginner
    LEVEL_2 = "2"  # Easy
    LEVEL_3 = "3"  # Medium
    LEVEL_4 = "4"  # Challenging
    LEVEL_5 = "5"  # Advanced

    # Legacy aliases for backward compatibility with in-flight jobs
    FOUNDATION = "FOUNDATION"
    LEGACY_L1 = "Level 1"
    LEGACY_L2 = "Level 2"
    LEGACY_L3 = "Level 3"
    LEGACY_L4 = "Level 4"
    LEGACY_L5 = "Level 5"

class Scene(BaseModel):
    scene_id: str
    text: str
    image_url: Optional[str] = None

class StoryInput(BaseModel):
    phonemes: List[str]
    story_idea: str
    difficulty_level: DifficultyLevel  # (Level 1, Level 2, Level 3)

class StoryOutput(BaseModel):
    story_id: str
    scenes: List[Scene]
    scene_count: int
    difficulty_level: str
    created_at: str

class TaskStatus(str, Enum):
    QUEUED = "QUEUED"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    DRAFT_READY = "DRAFT_READY"

class TaskProgress(BaseModel):
    task_id: str
    status: TaskStatus
    progress: float
    message: Optional[str] = None
    story_output: Optional[StoryOutput] = None
    pdf_url: Optional[str] = None 
