# phonics_maker/audio_generation/audio_types.py
"""
Data models for audio narration generation.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from enum import Enum


class AudioVoiceStyle(str, Enum):
    """Voice style presets for children's story narration."""
    WARM = "warm"           # Gentle, nurturing tone
    PLAYFUL = "playful"     # Energetic, fun tone
    CALM = "calm"           # Soft, relaxing tone (bedtime stories)
    DRAMATIC = "dramatic"   # Expressive, theatrical


@dataclass
class AudioConfig:
    """Configuration for audio generation."""
    enabled: bool = True
    voice_style: AudioVoiceStyle = AudioVoiceStyle.WARM
    speed: float = 0.9          # Slightly slower for children to follow
    format: str = "mp3"         # Output format
    sample_rate: int = 44100    # CD quality
    bitrate: str = "128k"
    locale: str = "en_us"       # Locale code: "en_us", "en_au", "en_gb", "en_nz", "en_ca", "fr", "es"


class AudioBillingError(Exception):
    """Raised when the audio API returns a billing/auth error (401/402/403).
    
    This is a non-retryable, fatal error. The entire audio generation loop
    should be aborted immediately — do NOT retry or attempt remaining scenes.
    """
    pass


@dataclass
class SceneAudio:
    """Audio data for a single scene."""
    scene_index: int
    scene_text: str
    audio_url: str              # Public URL on DO Spaces
    audio_local_path: str       # Local temp path before upload
    duration_seconds: float = 0.0
    file_size_bytes: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "scene_index": self.scene_index,
            "scene_text": self.scene_text,
            "audio_url": self.audio_url,
            "duration_seconds": self.duration_seconds,
            "file_size_bytes": self.file_size_bytes,
        }


@dataclass
class BookAudioManifest:
    """
    Complete audio manifest for a book.
    Stored and served to the /listen/[bookId] frontend page.
    """
    book_id: str
    title: str
    phonemes: List[str]
    scenes: List[SceneAudio] = field(default_factory=list)
    total_duration_seconds: float = 0.0
    listen_url: str = ""        # e.g. https://phonicsmaker.com/listen/abc123
    qr_code_path: str = ""      # Local path to generated QR code image
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "book_id": self.book_id,
            "title": self.title,
            "phonemes": self.phonemes,
            "scenes": [s.to_dict() for s in self.scenes],
            "total_duration_seconds": self.total_duration_seconds,
            "listen_url": self.listen_url,
        }
    
    def to_template_data(self) -> Dict[str, Any]:
        """Data for the back cover PDF template."""
        # Strip protocol for cleaner display
        display = self.listen_url
        for prefix in ("https://", "http://"):
            if display.startswith(prefix):
                display = display[len(prefix):]
                break
        
        return {
            "listen_url": self.listen_url,
            "display_url": display,
            "qr_code_path": self.qr_code_path,
            "total_duration": self._format_duration(self.total_duration_seconds),
            "num_scenes": len(self.scenes),
            "book_title": self.title,
        }
    
    @staticmethod
    def _format_duration(seconds: float) -> str:
        """Format seconds as 'Xm Ys'."""
        mins = int(seconds // 60)
        secs = int(seconds % 60)
        if mins > 0:
            return f"{mins}m {secs}s"
        return f"{secs}s"
