# phonics_maker/pdf_generation/text_processor.py

from typing import List, Optional
import os
import asyncio
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
from pathlib import Path
from app.core.config.logger import logger
from app.db.models.image import SceneImage
from app.db.models.story import DifficultyLevel
from app.phonics_maker.pdf_generation.image_processor import ImageProcessor
from app.phonics_maker.image_generation.image_service import ImageService

# ── Accessibility text rendering constants ─────────────────────────────
# For CVI/BVI styles: skip dynamic colour sampling, force max-contrast text.
ACCESSIBILITY_TEXT_COLOR = (0, 0, 0)        # Black (BGR)
ACCESSIBILITY_STROKE_COLOR = (255, 255, 255) # White (BGR)
ACCESSIBILITY_FONT_SCALE_MULTIPLIER = 1.3   # 30% larger text
ACCESSIBILITY_STROKE_THICKNESS = 6           # Thicker outline (default: 4)
ACCESSIBILITY_LETTER_SPACING = 5             # Wider spacing (default: 3)


def get_font_scale_for_difficulty(difficulty_level) -> float:
    """
    Get appropriate font scale factor based on difficulty level.

    Accepts DifficultyLevel enum, raw strings ("1"-"5"), or legacy
    strings ("FOUNDATION", "Level 1", etc.) and resolves to the
    correct font scale.

    Args:
        difficulty_level: The difficulty level (enum, "1"-"5", or legacy string)

    Returns:
        Font scale factor as a float
    """
    # Normalise to a plain string regardless of input type
    raw = str(difficulty_level.value if hasattr(difficulty_level, 'value') else difficulty_level)

    # Primary map keyed by the new "1"-"5" strings
    font_scale_map = {
        "1": 0.7000,  # Beginner  – largest text
        "2": 0.6900,  # Easy
        "3": 0.6800,  # Medium
        "4": 0.6700,  # Challenging
        "5": 0.6500,  # Advanced  – smallest text
    }

    # Legacy → new key mapping (same as prompts.LEGACY_DIFFICULTY_MAP)
    legacy_map = {
        "FOUNDATION": "1",
        "Level 1": "2",
        "Level 2": "3",
        "Level 3": "4",
        "Level 4": "4",
        "Level 5": "5",
    }

    key = raw if raw in font_scale_map else legacy_map.get(raw)
    if key is None:
        logger.warning(f"Unrecognised difficulty level '{raw}', defaulting to '1'")
        key = "1"

    return font_scale_map[key]


def add_text_to_image(
    image: SceneImage,
    text: str,
    phonemes: List[str],
    difficulty_level: DifficultyLevel,
    task_temp_dir: Path,
    font_path: str,
    is_free: bool = False,
    logo_path: Optional[str] = None,
    illustration_style: Optional[str] = None,
) -> str:
    """
    Add scene text to an image with appropriate styling based on difficulty level.

    Args:
        image: The image object
        text: Text to add to the image
        phonemes: List of phonemes to highlight
        difficulty_level: Difficulty level of the story
        task_temp_dir: Directory for temporary files
        font_path: Path to the font file
        is_free: Whether this is a free version (adds watermark)
        logo_path: Path to logo for watermarking free versions
        illustration_style: Illustration style ID — accessibility styles trigger high-contrast overrides

    Returns:
        URL to the processed image
    """
    try:
        import cv2

        # Create temp file path for processed image
        image_filename = os.path.basename(image.image_url.replace("file://", ""))
        processed_image_path = os.path.join(
            task_temp_dir, f"processed_{image_filename}"
        )

        # Read the image once — reused for colour sampling, edge detection, and text overlay
        clean_path = image.image_url.replace("file://", "")
        cv2_image = cv2.imread(clean_path)

        # ── Accessibility override: force high-contrast text for CVI/BVI ──
        is_accessible = ImageService.is_accessibility_style(illustration_style)

        if is_accessible:
            # Skip KMeans colour sampling — use guaranteed max-contrast colours
            text_color = ACCESSIBILITY_TEXT_COLOR
            stroke_color = ACCESSIBILITY_STROKE_COLOR
            logger.info(f"Accessibility style '{illustration_style}' — using forced high-contrast text")
        else:
            # Standard: sample optimal colours from the image (reuse loaded data)
            colors = ImageProcessor.get_optimized_text_stroke_colors(image.image_url, preloaded_image=cv2_image)
            stroke_color = colors["stroke_color"]
            text_color = colors["text_color"]

        # Get font scale based on difficulty level
        font_scale = get_font_scale_for_difficulty(difficulty_level)

        # Boost font for accessibility styles
        if is_accessible:
            font_scale *= ACCESSIBILITY_FONT_SCALE_MULTIPLIER
            logger.info(f"Accessibility font scale boosted to {font_scale:.4f}")

        # Determine stroke/spacing (accessibility gets thicker, wider)
        stroke_thickness = ACCESSIBILITY_STROKE_THICKNESS if is_accessible else 6
        letter_spacing = ACCESSIBILITY_LETTER_SPACING if is_accessible else 3

        # Process the image with child-friendly styling (reuse loaded data)
        output_path = ImageProcessor.add_text_to_image(
            image_path=image.image_url,
            text=text,
            output_path=processed_image_path,
            font_path=font_path,
            phonemes=phonemes,
            use_weighted_cog=True,
            font_scale=font_scale,
            text_color=text_color,
            stroke_color=stroke_color,
            stroke_thickness=stroke_thickness,
            letter_spacing=letter_spacing,
            preloaded_image=cv2_image,
        )

        # Add watermark for free version
        if is_free and logo_path:
            output_path = ImageProcessor.add_logo_watermark(
                image_path=output_path,
                logo_path=logo_path,
                opacity=0.7,
                scale_factor=0.6,
                position="center",
                repeat=True,
                diagonal=True,
            )

        logger.info(f"Processed image : {image.scene_id}")

        # Return file URL to the processed image
        return f"file://{output_path}"
    except Exception as e:
        logger.error(f"Error adding text to image: {str(e)}")
        # Return original image if processing fails
        return image.image_url


def _add_phonicsmaker_footer(image_path: str, output_path: str) -> None:
    """
    Overlay a small 'Made with PhonicsMaker.com' credit at the bottom of the cover.
    Everything else (title, focus sounds) is baked into the AI-generated image.
    """
    from PIL import Image, ImageDraw, ImageFont
    import os

    pil_image = Image.open(image_path).convert("RGB")
    draw = ImageDraw.Draw(pil_image)
    w, h = pil_image.size

    label = "A Story by PhonicsMaker"

    # Try to use a small system font; fall back to PIL default
    font_size = max(18, int(w * 0.025))
    try:
        font = ImageFont.load_default(font_size)
    except Exception:
        font = ImageFont.load_default()

    # Measure text
    bbox = draw.textbbox((0, 0), label, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]

    padding = int(h * 0.012)
    bar_height = th + padding * 2

    # Semi-transparent dark bar at the very bottom
    overlay = Image.new("RGBA", pil_image.size, (0, 0, 0, 0))
    overlay_draw = ImageDraw.Draw(overlay)
    overlay_draw.rectangle(
        [(0, h - bar_height), (w, h)],
        fill=(0, 0, 0, 160),
    )
    pil_image = Image.alpha_composite(pil_image.convert("RGBA"), overlay).convert("RGB")
    draw = ImageDraw.Draw(pil_image)

    # Centred white text
    tx = (w - tw) // 2
    ty = h - bar_height + padding
    draw.text((tx, ty), label, font=font, fill=(255, 255, 255))

    pil_image.save(output_path, "JPEG", quality=75)


async def create_cover_image(
    cover_image: SceneImage,
    story_title: str,
    phonemes: List[str],
    task_temp_dir: Path,
    heading_font_path: str,
    series_info: Optional[dict] = None,
) -> SceneImage:
    """
    Create a cover image with title and phoneme focus badge.

    Args:
        cover_image: Original cover image
        story_title: Title of the story
        phonemes: List of phonemes in the story
        task_temp_dir: Directory for temporary files
        heading_font_path: Path to heading font

    Returns:
        Processed cover image object
    """
    logger.info("Creating cover image with title...")

    # Track original URL for re-download retries
    original_cover_url = cover_image.image_url

    # Use cached file from validation if available
    if cover_image.cached_path and os.path.exists(cover_image.cached_path):
        local_image_path = cover_image.cached_path
        cover_image = SceneImage(
            scene_id=cover_image.scene_id,
            image_url=local_image_path,
            prompt=cover_image.prompt,
            created_at=cover_image.created_at,
        )
    elif cover_image.image_url.startswith("http"):
        # Handle remote images — download first
        try:
            downloaded_path = ImageProcessor.download_image(
                cover_image.image_url, task_temp_dir
            )
            # download_image returns file:// prefixed path — strip for PIL
            local_image_path = downloaded_path.replace("file://", "")
            cover_image = SceneImage(
                scene_id=cover_image.scene_id,
                image_url=local_image_path,
                prompt=cover_image.prompt,
                created_at=cover_image.created_at,
            )
        except Exception as e:
            logger.error(f"Failed to download cover image: {e}")
            local_image_path = cover_image.image_url.replace("file://", "")
    else:
        # Strip file:// prefix if present for PIL compatibility
        local_image_path = cover_image.image_url.replace("file://", "")

    # Validate the cover image — retry download if corrupt
    if not ImageProcessor.validate_image_file(local_image_path):
        logger.error(f"Cover image validation failed: {local_image_path}")
        if original_cover_url.startswith("http"):
            # Re-download with up to 2 retries
            for attempt in range(1, 3):
                logger.info(f"Re-downloading cover image (attempt {attempt}/2)...")
                try:
                    # Remove corrupt file
                    if os.path.exists(local_image_path):
                        os.remove(local_image_path)
                    await asyncio.sleep(1)  # Brief pause before retry
                    downloaded_path = ImageProcessor.download_image(
                        original_cover_url, task_temp_dir
                    )
                    local_image_path = downloaded_path.replace("file://", "")
                    if ImageProcessor.validate_image_file(local_image_path):
                        logger.info(f"Cover image re-download succeeded on attempt {attempt}")
                        cover_image = SceneImage(
                            scene_id=cover_image.scene_id,
                            image_url=local_image_path,
                            prompt=cover_image.prompt,
                            created_at=cover_image.created_at,
                        )
                        break
                    else:
                        logger.warning(f"Cover image still invalid after re-download attempt {attempt}")
                except Exception as e:
                    logger.error(f"Cover image re-download attempt {attempt} failed: {e}")
            else:
                raise ValueError(f"Cover image is corrupt after all retry attempts: {local_image_path}")
        else:
            raise ValueError(f"Local cover image is corrupt/unreadable: {local_image_path}")

    # Create output path for processed cover
    image_filename = os.path.basename(local_image_path)
    processed_image_path = os.path.join(
        task_temp_dir, f"processed_cover_{image_filename}"
    )

    # The title and focus sounds are now baked into the AI-generated image
    # via the structured cover prompt.  "Made with PhonicsMaker.com" is rendered
    # by the HTML cover_page_template.html — no image-level overlay needed.
    # Just copy the validated image to the processed path.
    import shutil
    shutil.copy2(local_image_path, processed_image_path)

    # Create new scene image with processed path
    processed_cover_image = SceneImage(
        scene_id=cover_image.scene_id,
        image_url=processed_image_path,
        prompt=cover_image.prompt,
        created_at=cover_image.created_at,
    )

    return processed_cover_image

def sync_add_text_to_image(*args, **kwargs):
    """Wrapper for add_text_to_image (now synchronous — kept for call-site compatibility)."""
    return add_text_to_image(*args, **kwargs)

def _process_single_image_worker(
    image: SceneImage,
    scene: str,
    phonemes: List[str],
    difficulty_level: DifficultyLevel,
    task_temp_dir: Path,
    font_path: str,
    is_free: bool,
    logo_path: Optional[str] = None,
    illustration_style: Optional[str] = None,
) -> SceneImage:
    try:
        processed_url = sync_add_text_to_image(
            image,
            scene,
            phonemes,
            difficulty_level,
            task_temp_dir,
            font_path,
            is_free,
            logo_path,
            illustration_style=illustration_style,
        )
        return SceneImage(
            scene_id=image.scene_id,
            image_url=processed_url,
            prompt=image.prompt,
            created_at=image.created_at,
        )
    except Exception as e:
        logger.error(f"Error processing image {image.scene_id}: {str(e)}")
        return image

def _process_single_image_worker_unpack(args):
    return _process_single_image_worker(*args)

async def process_images(
    scenes: List[str],
    images: List[SceneImage],
    phonemes: List[str],
    difficulty_level: DifficultyLevel,
    is_free: bool,
    task_temp_dir: Path,
    font_path: str,
    logo_path: str = None,
    illustration_style: Optional[str] = None,
) -> List[SceneImage]:
    """
    Process all scene images by adding highlight text from each scene using ProcessPoolExecutor for CPU-bound rendering.
    """
    processed_images = []
    
    # Download images (skip if already cached locally from validation)
    def download_image(image: SceneImage):
        if image.cached_path and os.path.exists(image.cached_path):
            return SceneImage(
                scene_id=image.scene_id,
                image_url=f"file://{image.cached_path}",
                prompt=image.prompt,
                created_at=image.created_at,
            )
        if image.image_url.startswith("http"):
            local_image_path = ImageProcessor.download_image(
                image.image_url, task_temp_dir
            )
            if local_image_path:
                return SceneImage(
                    scene_id=image.scene_id,
                    image_url=local_image_path,
                    prompt=image.prompt,
                    created_at=image.created_at,
                )
            else:
                logger.error(f"Failed to download image {image.image_url}")
                return image
        return image

    # Download images first using thread pool (I/O bound)
    with ThreadPoolExecutor(max_workers=12) as executor:
        logger.info("Downloading images...")
        images = list(executor.map(download_image, images))
        
    # Then process images with text using process pool (CPU bound)
    logger.info(f"Processing {len(images)} images with text using ProcessPoolExecutor...")
    worker_args = [
        (
            images[i],
            scene,
            phonemes,
            difficulty_level,
            task_temp_dir,
            font_path,
            is_free,
            logo_path,
            illustration_style,
        )
        for i, scene in enumerate(scenes)
        if i < len(images)
    ]
    
    # Use ProcessPoolExecutor to bypass the GIL and utilize multiple cores
    with ProcessPoolExecutor(max_workers=4) as process_executor:
        results = list(process_executor.map(_process_single_image_worker_unpack, worker_args))

    # Filter out None results and extend with remaining unprocessed images
    processed_images = [img for img in results if img is not None]
    processed_images.extend(images[len(processed_images):])

    return processed_images