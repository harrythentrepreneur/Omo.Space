# core/models/image.py

from typing import Optional
from pydantic import BaseModel, Field

class SceneImage(BaseModel):
    scene_id: str
    image_url: str
    prompt: str
    created_at: str
    seed: Optional[int] = None
    cached_path: Optional[str] = Field(default=None, exclude=True)  # Local file path from validation download; excluded from JSON serialization