# phonics_maker/audio_generation/audio_service.py
"""
Audio narration service using Fish Audio TTS API.

Generates MP3 audio for each scene of a book, uploads to DO Spaces,
and produces a BookAudioManifest for the frontend audio player page.
"""

import os
import asyncio
import json
import traceback
from pathlib import Path
from typing import List, Optional, Dict, Any

import httpx

from app.core.config.config import settings
from app.core.config.logger import logger
from app.core.storage.file_storage import upload_result
from app.phonics_maker.audio_generation.audio_types import (
    AudioConfig,
    AudioBillingError,
    AudioVoiceStyle,
    SceneAudio,
    BookAudioManifest,
)
from app.phonics_maker.audio_generation.qr_generator import generate_listen_qr


# ═══════════════════════════════════════════════════════════════════
# Fish Audio API Constants
# ═══════════════════════════════════════════════════════════════════
FISH_AUDIO_TTS_URL = "https://api.fish.audio/v1/tts"

# Emotion/style prefixes for Fish Audio S1 model's emotion control
VOICE_STYLE_PROMPTS = {
    "en": {
        AudioVoiceStyle.WARM: (
            "Read this children's story in a warm, gentle, nurturing voice. "
            "Speak clearly and at a pace suitable for young children learning to read. "
            "Emphasize target phonics sounds slightly."
        ),
        AudioVoiceStyle.PLAYFUL: (
            "Read this children's story in a fun, playful, energetic voice. "
            "Use expressive tones to keep children engaged. "
            "Speak clearly for young learners."
        ),
        AudioVoiceStyle.CALM: (
            "Read this children's story in a soft, calm, soothing voice. "
            "Perfect for bedtime reading. Speak slowly and clearly "
            "for children learning to read."
        ),
        AudioVoiceStyle.DRAMATIC: (
            "Read this children's story with dramatic, theatrical expression. "
            "Use varied tones for different characters. "
            "Speak clearly for children learning phonics."
        ),
    },
    "fr": {
        AudioVoiceStyle.WARM: (
            "Lisez cette histoire pour enfants d'une voix chaleureuse et douce. "
            "Parlez clairement et à un rythme adapté aux jeunes enfants qui apprennent à lire."
        ),
        AudioVoiceStyle.PLAYFUL: (
            "Lisez cette histoire pour enfants d'une voix amusante et énergique. "
            "Utilisez des tons expressifs pour captiver les enfants."
        ),
        AudioVoiceStyle.CALM: (
            "Lisez cette histoire pour enfants d'une voix douce et apaisante. "
            "Parfait pour la lecture du soir. Parlez lentement et clairement."
        ),
        AudioVoiceStyle.DRAMATIC: (
            "Lisez cette histoire pour enfants avec une expression dramatique et théâtrale. "
            "Utilisez des tons variés pour les différents personnages."
        ),
    },
    "es": {
        AudioVoiceStyle.WARM: (
            "Lee este cuento infantil con una voz cálida, suave y cariñosa. "
            "Habla con claridad y a un ritmo adecuado para niños pequeños que están aprendiendo a leer."
        ),
        AudioVoiceStyle.PLAYFUL: (
            "Lee este cuento infantil con una voz divertida, juguetona y enérgica. "
            "Usa tonos expresivos para mantener a los niños interesados."
        ),
        AudioVoiceStyle.CALM: (
            "Lee este cuento infantil con una voz suave, tranquila y relajante. "
            "Perfecto para la hora de dormir. Habla despacio y con claridad."
        ),
        AudioVoiceStyle.DRAMATIC: (
            "Lee este cuento infantil con expresión dramática y teatral. "
            "Usa tonos variados para los diferentes personajes."
        ),
    },
}

# Localized title narration intro templates
TITLE_INTRO_TEMPLATES = {
    "en": "{title}. A story from PhonicsMaker.",
    "fr": "{title}. Une histoire de PhonicsMaker.",
    "es": "{title}. Una historia de PhonicsMaker.",
}


class AudioGenerationError(Exception):
    """Raised when audio generation fails."""
    pass


class AudioService:
    """
    Service for generating narration audio using Fish Audio TTS.
    
    Usage:
        audio_service = AudioService()
        manifest = await audio_service.generate_book_audio(
            book_id="abc123",
            title="The Shell Shore",
            scenes=["Sam found a shell...", "The waves crashed..."],
            phonemes=["sh", "ch"],
        )
    """
    
    def __init__(self, config: Optional[AudioConfig] = None):
        self.config = config or AudioConfig()
        self.api_key = settings.FISH_AUDIO_API_KEY
        self.model = settings.FISH_AUDIO_MODEL
        self.public_base_url = settings.AUDIO_PUBLIC_BASE_URL
        
        # Select voice based on locale — cascading fallback:
        #   locale-specific voice → default FISH_AUDIO_VOICE_ID
        locale = self.config.locale.lower()
        self.lang = locale.split("_")[0]  # "en", "fr", "es"
        
        voice_map = {
            # English accents
            "en_us": settings.FISH_AUDIO_VOICE_ID_US,
            "en_gb": settings.FISH_AUDIO_VOICE_ID_UK,
            "en_uk": settings.FISH_AUDIO_VOICE_ID_UK,   # alias
            "en_au": settings.FISH_AUDIO_VOICE_ID_AU,
            "en_nz": settings.FISH_AUDIO_VOICE_ID_NZ,
            "en_ca": settings.FISH_AUDIO_VOICE_ID_CA,
            # Non-English languages
            "fr":    settings.FISH_AUDIO_VOICE_ID_FR,
            "es":    settings.FISH_AUDIO_VOICE_ID_ES,
        }
        # Use locale-specific voice, or fall back to default
        self.voice_id = voice_map.get(locale) or settings.FISH_AUDIO_VOICE_ID
        logger.info(f"🎙️ Audio locale: {locale}, lang: {self.lang}, voice_id: {self.voice_id}")
        
        if not self.api_key:
            logger.warning("FISH_AUDIO_API_KEY not set. Audio generation will be skipped.")
    
    async def generate_book_audio(
        self,
        book_id: str,
        title: str,
        scenes: List[str],
        phonemes: List[str],
        temp_dir: Optional[Path] = None,
        share_url: Optional[str] = None,
    ) -> BookAudioManifest:
        """
        Generate audio narration for all scenes in a book.
        
        Args:
            book_id: Unique identifier for the book / task
            title: Book title (for the manifest)
            scenes: List of scene text strings
            phonemes: Target phonemes (for the manifest metadata)
            temp_dir: Temp directory for audio files before upload
            share_url: Optional short share URL (e.g. https://phonicsmaker.com/s/AbCd1234)
                       If provided, used for QR code + back cover instead of /listen/{bookId}
            
        Returns:
            BookAudioManifest with all scene audio URLs and the listen page URL
        """
        if not self.api_key:
            raise AudioGenerationError("Fish Audio API key not configured")
        
        # Set up temp directory
        if temp_dir is None:
            temp_dir = Path(__file__).resolve().parent.parent.parent.parent / "temp" / "audio"
        audio_temp_dir = temp_dir / book_id
        audio_temp_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"🎙️ Generating audio for book '{title}' ({len(scenes)} scenes + title)")
        
        # Generate audio for each scene
        scene_audios: List[SceneAudio] = []
        
        # ── Shared HTTP client for all TTS calls (avoids connection churn) ──
        # Pool limits tuned for concurrent TTS generation
        pool_limits = httpx.Limits(
            max_connections=10,
            max_keepalive_connections=5,
            keepalive_expiry=30,
        )
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(60.0, connect=15.0),
            limits=pool_limits,
        ) as http_client:
            # ── Scene 0: Title narration (plays on cover page) ──────────
            # The PDF structure is: cover (page 0), scene 1 (page 1), scene 2 (page 2), etc.
            # We generate the title as scene_index=0 so it maps to the cover page.
            lang = self.lang
            phoneme_list = ", ".join(phonemes) if phonemes else (
                "letter sounds" if lang == "en" else
                "lettres" if lang == "fr" else
                "letras" if lang == "es" else "letter sounds"
            )
            title_template = TITLE_INTRO_TEMPLATES.get(lang, TITLE_INTRO_TEMPLATES["en"])
            title_text = title_template.format(title=title, phonemes=phoneme_list)
            try:
                title_audio = await self._generate_scene_audio(
                    scene_index=0,
                    scene_text=title_text,
                    book_id=book_id,
                    output_dir=audio_temp_dir,
                    http_client=http_client,
                )
                scene_audios.append(title_audio)
                logger.info(
                    f"  ✅ Title narration generated "
                    f"({title_audio.duration_seconds:.1f}s, "
                    f"{title_audio.file_size_bytes / 1024:.1f}KB)"
                )
            except AudioBillingError:
                raise  # Fatal billing error — abort entire audio generation
            except Exception as e:
                logger.error(f"  ❌ Title narration failed: {type(e).__name__}: {e!r}")
            
            # ── Scenes 1..N: Story narration (parallel for speed) ──
            tts_semaphore = asyncio.Semaphore(5)  # Limit concurrent Fish Audio API calls
            billing_abort = asyncio.Event()       # Set on first 402 — all scenes skip immediately

            async def _generate_one(i: int, text: str) -> Optional[SceneAudio]:
                async with tts_semaphore:
                    # Fast-exit if another scene already got a billing error
                    if billing_abort.is_set():
                        return None
                    try:
                        sa = await self._generate_scene_audio(
                            scene_index=i + 1,
                            scene_text=text,
                            book_id=book_id,
                            output_dir=audio_temp_dir,
                            http_client=http_client,
                        )
                        logger.info(
                            f"  ✅ Scene {i + 1}/{len(scenes)} generated "
                            f"({sa.duration_seconds:.1f}s, "
                            f"{sa.file_size_bytes / 1024:.1f}KB)"
                        )
                        return sa
                    except AudioBillingError:
                        billing_abort.set()  # Signal all other scenes to skip
                        logger.error(
                            f"  💰 Billing error on scene {i + 1}/{len(scenes)} — "
                            f"aborting remaining audio generation"
                        )
                        return None
                    except Exception as e:
                        logger.error(f"  ❌ Scene {i + 1}/{len(scenes)} failed: {type(e).__name__}: {e!r}")
                        return None

            results = await asyncio.gather(
                *[_generate_one(i, text) for i, text in enumerate(scenes)]
            )
            scene_audios.extend(sa for sa in results if sa is not None)

        
        if not scene_audios:
            raise AudioGenerationError("All scene audio generation failed")
        
        # Upload audio files to DO Spaces (parallel)
        logger.info(f"📤 Uploading {len(scene_audios)} audio files...")

        async def _upload_one(sa: SceneAudio) -> None:
            try:
                audio_url = await self._upload_audio(sa, book_id)
                sa.audio_url = audio_url
                logger.info(f"  ✅ Uploaded scene {sa.scene_index + 1}: {audio_url}")
            except Exception as e:
                logger.error(f"  ❌ Upload failed for scene {sa.scene_index + 1}: {e}")

        await asyncio.gather(*[_upload_one(sa) for sa in scene_audios])
        
        # Calculate total duration
        total_duration = sum(s.duration_seconds for s in scene_audios)
        
        # Generate listen URL — prefer short share URL if provided
        if share_url:
            listen_url = share_url
            logger.info(f"🔗 Using short share URL for QR code: {listen_url}")
        else:
            listen_url = f"{self.public_base_url}/listen/{book_id}"
        
        # Generate QR code for back cover
        qr_path = str(audio_temp_dir / "listen_qr.png")
        generate_listen_qr(listen_url, qr_path)
        logger.info(f"📱 QR code generated: {qr_path}")
        
        # Upload the manifest as JSON (for the frontend to fetch)
        manifest = BookAudioManifest(
            book_id=book_id,
            title=title,
            phonemes=phonemes,
            scenes=scene_audios,
            total_duration_seconds=total_duration,
            listen_url=listen_url,
            qr_code_path=qr_path,
        )
        
        # Save manifest JSON alongside audio files
        manifest_path = audio_temp_dir / "manifest.json"
        with open(manifest_path, "w") as f:
            json.dump(manifest.to_dict(), f, indent=2)
        
        # Upload manifest to storage
        try:
            manifest_url = await self._upload_file(
                str(manifest_path), book_id, "audio/manifest.json", "application/json"
            )
            logger.info(f"📋 Manifest uploaded: {manifest_url}")
        except Exception as e:
            logger.error(f"Failed to upload manifest: {e}")
        
        logger.info(
            f"🎧 Audio generation complete! "
            f"{len(scene_audios)} scenes, {total_duration:.1f}s total. "
            f"Listen: {listen_url}"
        )
        
        return manifest
    
    async def _generate_scene_audio(
        self,
        scene_index: int,
        scene_text: str,
        book_id: str,
        output_dir: Path,
        http_client: httpx.AsyncClient,
    ) -> SceneAudio:
        """
        Generate audio for a single scene using Fish Audio API.
        """
        # Build the TTS request
        output_path = output_dir / f"scene_{scene_index + 1}.{self.config.format}"
        
        # Prepare the request headers — model goes in a header per Fish Audio docs
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "model": self.model or "s1",  # Fish Audio recommends "s1"
        }
        
        payload: Dict[str, Any] = {
            "text": scene_text,
            "format": self.config.format,
            "mp3_bitrate": 128,
            "normalize": True,
            "latency": "normal",  # Best quality
            "chunk_length": 200,
            "prosody": {
                "speed": self.config.speed,
                "volume": 0,
            },
        }
        
        # Add voice reference if configured
        if self.voice_id:
            payload["reference_id"] = self.voice_id
        
        # Make the API call with retries
        # ConnectError gets 5 attempts with longer backoff; other errors get 3
        max_retries = 5
        last_error = None
        
        for attempt in range(max_retries):
            try:
                response = await http_client.post(
                    FISH_AUDIO_TTS_URL,
                    headers=headers,
                    json=payload,
                )
                
                if response.status_code != 200:
                    error_text = response.text
                    
                    # ── Fast-fail on billing / auth errors ─────────────
                    # 401 = Unauthorized, 402 = Payment Required, 403 = Forbidden
                    # These are non-retryable — abort immediately.
                    if response.status_code in (401, 402, 403):
                        logger.error(
                            f"❌ BILLING/AUTH ERROR (HTTP {response.status_code}) from Fish Audio — "
                            f"aborting all audio generation. Body: {error_text[:300]}"
                        )
                        raise AudioBillingError(
                            f"Fish Audio API returned {response.status_code}: {error_text[:200]}"
                        )
                    
                    logger.warning(
                        f"Fish Audio API error (attempt {attempt + 1}): "
                        f"status={response.status_code}, body={error_text[:200]}"
                    )
                    last_error = AudioGenerationError(
                        f"Fish Audio API returned {response.status_code}: {error_text[:200]}"
                    )
                    if attempt < max_retries - 1:
                        await asyncio.sleep(2 ** attempt)  # Exponential backoff
                    continue
                
                # Write audio data to file
                audio_data = response.content
                with open(output_path, "wb") as f:
                    f.write(audio_data)
                
                file_size = os.path.getsize(output_path)
                
                # Estimate duration from file size
                # MP3 at 128kbps: ~16KB per second
                estimated_duration = file_size / (128 * 1024 / 8)
                
                return SceneAudio(
                    scene_index=scene_index,
                    scene_text=scene_text,
                    audio_url="",  # Will be set after upload
                    audio_local_path=str(output_path),
                    duration_seconds=estimated_duration,
                    file_size_bytes=file_size,
                )
                    
            except (httpx.ConnectError, httpx.PoolTimeout) as e:
                # TLS handshake / connection pool exhaustion — wait longer before retry
                backoff = 3 * (attempt + 1)  # 3s, 6s, 9s, 12s, 15s
                logger.warning(
                    f"Fish Audio connection error (attempt {attempt + 1}/{max_retries}): "
                    f"{type(e).__name__} — retrying in {backoff}s"
                )
                last_error = AudioGenerationError(f"Connection error: {type(e).__name__}: {e!r}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(backoff)
            except httpx.TimeoutException as e:
                logger.warning(f"Fish Audio API timeout (attempt {attempt + 1}): {e}")
                last_error = AudioGenerationError(f"API timeout: {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(2 ** attempt)
            except AudioBillingError:
                raise  # Non-retryable billing/auth error — propagate immediately
            except Exception as e:
                logger.error(
                    f"Unexpected error in audio generation (attempt {attempt + 1}): "
                    f"{type(e).__name__}: {e!r}\n{traceback.format_exc()}"
                )
                last_error = AudioGenerationError(f"Unexpected error: {type(e).__name__}: {e!r}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(2 ** attempt)
        
        raise last_error or AudioGenerationError("Audio generation failed after all retries")
    
    async def _upload_audio(self, scene_audio: SceneAudio, book_id: str) -> str:
        """Upload a scene's audio file to DO Spaces."""
        return await self._upload_file(
            scene_audio.audio_local_path,
            book_id,
            f"audio/scene_{scene_audio.scene_index + 1}.{self.config.format}",
            "audio/mpeg",
        )
    
    async def _upload_file(
        self,
        local_path: str,
        book_id: str,
        object_suffix: str,
        content_type: str,
    ) -> str:
        """Upload a file to DO Spaces under the book's audio directory."""
        import boto3
        from botocore.client import Config
        
        if not os.path.exists(local_path):
            raise FileNotFoundError(f"File not found: {local_path}")
        
        session = boto3.session.Session()
        spaces_client = session.client(
            "s3",
            region_name=settings.SPACES_REGION,
            endpoint_url=f"https://{settings.SPACES_ENDPOINT}",
            aws_access_key_id=settings.SPACES_KEY,
            aws_secret_access_key=settings.SPACES_SECRET,
            config=Config(signature_version="s3v4"),
        )
        
        bucket_name = settings.SPACES_NAME
        object_name = f"generated_pdfs/{book_id}/{object_suffix}"
        
        spaces_client.upload_file(
            local_path,
            bucket_name,
            object_name,
            ExtraArgs={
                "ACL": "public-read",
                "ContentType": content_type,
            },
        )
        
        # Use CDN endpoint for public URLs when available
        cdn_endpoint = settings.SPACES_CDN_ENDPOINT or settings.SPACES_ENDPOINT
        public_url = f"https://{bucket_name}.{cdn_endpoint}/{object_name}"
        return public_url
