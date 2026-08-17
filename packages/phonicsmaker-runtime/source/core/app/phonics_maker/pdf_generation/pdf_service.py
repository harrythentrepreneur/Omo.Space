# phonics_maker/pdf_generation/pdf_service.py

from typing import List, Optional
from datetime import datetime
import asyncio
import io
import os
import re
from pathlib import Path
from app.core.config.logger import logger
from app.core.config.config import settings
from app.db.models.image import SceneImage
from app.db.models.story import DifficultyLevel
from app.db.models.pdf import PDFGenerationResponse

# Import newly refactored modules
from app.phonics_maker.pdf_generation.html_renderer import HTMLRenderer
from app.phonics_maker.pdf_generation.pdf_generator import generate_pdf_from_html_pages, PRINT_VARIANT_SUFFIX
from app.phonics_maker.pdf_generation.pptx_generator import generate_pptx_from_images
from app.phonics_maker.pdf_generation.text_processor import (
    create_cover_image,
    process_images,
)
from app.phonics_maker.pdf_generation.image_processor import ImageProcessor
from app.phonics_maker.pdf_generation.file_utils import (
    make_filesystem_safe,
    get_task_temp_dir,
    ensure_directory_exists,
)

# Activity generation for end-of-book worksheets
from app.phonics_maker.activity_generation.activity_service import ActivityService
from app.phonics_maker.activity_generation.activity_types import ActivityConfig

# Audio narration generation
from app.phonics_maker.audio_generation.audio_service import AudioService
from app.phonics_maker.audio_generation.audio_types import AudioConfig, BookAudioManifest


def highlight_phonemes_in_html(text: str, phonemes: List[str]) -> str:
    """
    Wrap phoneme occurrences in the scene text with <span class="highlight"> tags.
    Used for non-classic layouts where text is rendered via HTML/CSS instead of PIL.

    Args:
        text: The scene text (may contain <br> tags from newline conversion)
        phonemes: List of phoneme strings to highlight (e.g. ['sh', 'ch', 'th'])

    Returns:
        HTML string with phoneme occurrences wrapped in highlight spans
    """
    # 1. Manual User Highlight Override (TipTap Editor <mark> or WhatsApp style)
    if '<mark' in text or '**' in text:
        # Priority to manual explicit highlights. Replace <mark> with span and skip auto-highlight
        if '**' in text:
            text = re.sub(r'\*\*(.*?)\*\*', r'<mark>\1</mark>', text) # Convert legacy
        text = re.sub(r'<mark[^>]*>', '<span class="highlight">', text)
        return text.replace('</mark>', '</span>')

    # 2. Legacy Auto-Highlighting Fallback
    if not phonemes:
        return text

    # Sort phonemes by length (longest first) to avoid partial matches
    # e.g. 'sh' should be matched before 's'
    sorted_phonemes = sorted(phonemes, key=len, reverse=True)

    # Build a regex pattern that matches any phoneme (case-insensitive)
    # Use word-boundary-aware matching within words
    escaped = [re.escape(p) for p in sorted_phonemes if p]
    if not escaped:
        return text

    pattern = re.compile('(' + '|'.join(escaped) + ')', re.IGNORECASE)

    # Split on HTML tags to avoid highlighting inside tags
    parts = re.split(r'(<[^>]+>)', text)
    result = []
    for part in parts:
        if part.startswith('<'):
            # HTML tag — pass through unchanged
            result.append(part)
        else:
            # Text content — apply highlighting
            result.append(pattern.sub(r'<span class="highlight">\1</span>', part))

    return ''.join(result)


def _visible_length(html_text: str) -> int:
    """Return character count ignoring HTML tags."""
    return len(re.sub(r'<[^>]+>', '', html_text))


def _measure_text_fits(text: str, font_size: int, layout: str, font_cfg) -> bool:
    """
    Render text at the given font size in a container matching the layout's
    text area dimensions. Returns True if text fits without overflow.

    Creates a minimal HTML page sized to the exact text container. If WeasyPrint
    renders it as a single page, the text fits. If >1 page, it overflowed.
    """
    from weasyprint import HTML

    if layout == "side_by_side":
        # Container: ~55% of A5 width minus padding → ~66mm wide, ~190mm tall
        container_w, container_h = 66, 190
        text_align = "left"
        pad_v, pad_h = 0, 0  # side_by_side padding handled by template
    else:  # picture_top
        # Container: 20% of A5 height (210mm) = 42mm, minus 4mm page padding-top = ~38mm,
        # minus template text-area padding (2mm top + 4mm bottom = 6mm) = ~32mm usable.
        # Width: A5 = 148mm - 8mm page padding - 14mm text padding × 96% max-width ≈ 121mm.
        container_w, container_h = 121, 38
        text_align = "center"
        pad_v, pad_h = 2, 7  # Match template: padding: 2mm 7mm 4mm 7mm (use top + sides)

    html = (
        f'<!DOCTYPE html><html><head><style>'
        f"@font-face {{ font-family: 'MF'; font-weight: 400; "
        f"src: url('file://{font_cfg.ttf_path}') format('truetype'); }}"
        f"@font-face {{ font-family: 'MF'; font-weight: 700; "
        f"src: url('file://{font_cfg.heading_ttf_path}') format('truetype'); }}"
        f'@page {{ size: {container_w}mm {container_h}mm; margin: 0; }}'
        f'body {{ margin: 0; padding: 0; }}'
        f"p {{ font-family: 'MF', sans-serif; font-size: {font_size}px; "
        f'font-weight: 700; line-height: 1.5; text-align: {text_align}; '
        f'margin: 0; padding: {pad_v}mm {pad_h}mm; '
        f'word-wrap: break-word; overflow-wrap: break-word; max-width: 96%; }}'
        f'.highlight {{ padding: 2px 5px; }}'
        f'</style></head><body><p>{text}</p></body></html>'
    )

    doc = HTML(string=html, base_url='/').render()
    return len(doc.pages) == 1


def _compute_font_size_heuristic(text: str, layout: str) -> int:
    """Fallback heuristic font sizing based on character count."""
    plain_len = _visible_length(text)

    if layout == "side_by_side":
        if plain_len <= 25:  return 34
        elif plain_len <= 50:  return 28
        elif plain_len <= 75:  return 24
        elif plain_len <= 110: return 20
        else:                  return 17
    else:  # picture_top
        if plain_len <= 20:  return 38
        elif plain_len <= 40:  return 32
        elif plain_len <= 60:  return 28
        elif plain_len <= 85:  return 24
        elif plain_len <= 110: return 20
        else:                  return 18


def compute_scene_font_size(text: str, layout: str = "picture_top", font_cfg=None) -> int:
    """
    Find the LARGEST font size that fits the text in the layout's container.

    Uses WeasyPrint to render text at progressively smaller sizes via binary
    search, returning the biggest font that doesn't overflow. This handles
    variable-width fonts, highlight spans, and any text content perfectly.

    Falls back to character-count heuristic if font_cfg is not provided or
    if measurement fails.
    """
    if font_cfg is None:
        return _compute_font_size_heuristic(text, layout)

    plain_len = _visible_length(text)

    if layout == "side_by_side":
        max_size, min_size = 36, 16
    else:  # picture_top
        max_size, min_size = 40, 16  # 16px minimum for readability by young learners

    # Very short text: skip measurement, always fits at max
    if plain_len <= 10:
        return max_size

    try:
        # Binary search for the largest fitting size
        best = min_size
        lo, hi = min_size, max_size
        while lo <= hi:
            mid = (lo + hi) // 2
            if _measure_text_fits(text, mid, layout, font_cfg):
                best = mid
                lo = mid + 1
            else:
                hi = mid - 1
        return best
    except Exception as e:
        logger.warning(f"Font size measurement failed, falling back to heuristic: {e}")
        return _compute_font_size_heuristic(text, layout)


async def generate_story_pdf(
    story_id: str,
    story_title: str,
    scenes: List[str],
    images: List[SceneImage],
    phonemes: List[str],
    difficulty_level: DifficultyLevel,
    is_free: bool,
    include_activities: bool = False,
    activity_config: Optional[ActivityConfig] = None,
    include_audio: bool = False,  # DISABLED: Fish Audio 402 "Insufficient Balance"
    audio_config: Optional[AudioConfig] = None,
    language_variant: Optional[str] = None,
    book_layout: Optional[str] = None,
    book_font: Optional[str] = None,
    focus_phonemes: Optional[List[str]] = None,  # V2: highlight only these (teaching targets)
    highlight_text: Optional[bool] = None,        # V2: whether to highlight phonemes at all (None/True = yes)
    illustration_style: Optional[str] = None,      # Accessibility: override text rendering for CVI/BVI styles
    morphology_focus: Optional[List[str]] = None,  # V2: morphology items to highlight (prefixes/suffixes/roots)
    series_info: Optional[dict] = None,  # Series badge info: {book_position, total_books, series_name}
    standard_codes: Optional[List[str]] = None,  # Audit-proof curriculum standard tags
    pre_generated_activities: Optional[tuple] = None,  # (List[Dict], AnswerKeyData) to skip regeneration
    pre_rendered_activities_html: Optional[List[str]] = None,  # pre-rendered HTML pages from frontend editor
    with_print_variant: bool = True,  # Also emit a smaller print-friendly combined PDF
) -> PDFGenerationResponse:
    """
    Generate a PDF from the story scenes and images, and a thumbnail from the cover.
    
    Args:
        story_id: Unique identifier for this story generation
        story_title: Title of the book
        scenes: List of scene text content
        images: List of SceneImage objects (cover + scenes)
        phonemes: Target phonemes for this book
        difficulty_level: Reading level/difficulty
        is_free: Whether this is a free-tier generation
        include_activities: Whether to add activity worksheets at the end
        activity_config: Configuration for which activities to include
        include_audio: Whether to generate audio narration for each scene
        audio_config: Configuration for audio generation (voice, speed, etc.)
    """
    try:
        logger.info(f"Generating PDF and thumbnail for story {story_id}...")

        # Set up paths
        base_dir = Path(__file__).resolve().parent.parent.parent.parent
        template_dir = base_dir / "templates"
        static_dir = base_dir / "static"
        temp_dir = base_dir / "temp" 
        output_dir = static_dir / "output" # PDF output, distinct from task_temp_dir for intermediates

        # Ensure directories exist
        ensure_directory_exists(temp_dir)
        ensure_directory_exists(output_dir) # For final PDF storage before upload
        
        # Task-specific temporary directory for all intermediate files
        task_temp_dir = get_task_temp_dir(temp_dir, story_id)
        logger.info(f"Using task temporary directory: {task_temp_dir}")


        # Resolve font and layout from book style config
        from app.phonics_maker.pdf_generation.font_config import resolve_font, resolve_layout
        logger.info(f"[BOOK_STYLE] book_layout={book_layout!r}, book_font={book_font!r}")
        font_cfg = resolve_font(book_font)
        layout_cfg = resolve_layout(book_layout)
        logger.info(f"[BOOK_STYLE] resolved → template={layout_cfg.template}, text_in_image={layout_cfg.text_in_image}, font={font_cfg.css_family}")

        # Set up resource paths using resolved font config
        font_path = font_cfg.ttf_path
        heading_font_path = font_cfg.heading_ttf_path
        logo_path = str(static_dir / "images/logo-dark.png")
        trial_image_path = str(static_dir / "images/trial-image.png")

        # Initialize HTML renderer
        html_renderer = HTMLRenderer(template_dir)

        # Validate inputs
        cover_image = images[0] if images else None
        if cover_image is None:
            raise ValueError("Cover image is required for PDF generation.")
        
        scene_images = images[1:] if len(images) > 1 else []

        # Process the cover image
        import time as _time
        _t_cover = _time.perf_counter()
        # This returns a SceneImage with image_url being a local path to the processed cover
        # V2: Only show focus (teaching target) sounds on the cover badge.
        # If no focus sounds are selected, pass an empty list so the badge is omitted.
        cover_phonemes = focus_phonemes if focus_phonemes is not None else []
        cover_morphology = morphology_focus if morphology_focus is not None else []
        # Combine focus phonemes + morphology for the cover badge display
        all_cover_items = cover_phonemes + cover_morphology
        processed_cover_image = await create_cover_image(
            cover_image, story_title,
            all_cover_items,
            task_temp_dir, heading_font_path,
            series_info=series_info,
        )
        logger.info(f"⏱️  [TIMING][pdf] Cover image processing: {_time.perf_counter() - _t_cover:.2f}s")
        
        # Branch rendering path based on layout
        _t_scene_proc = _time.perf_counter()
        if layout_cfg.text_in_image:
            # CLASSIC LAYOUT: bake text onto images via PIL (original behavior)
            # V2: Only highlight focus (teaching target) sounds in the story text.
            # When highlight_text is explicitly False, skip phoneme highlighting entirely.
            if highlight_text is False:
                highlight_phonemes = []
            else:
                fp = focus_phonemes if focus_phonemes else []
                mf = morphology_focus if morphology_focus else []
                highlight_phonemes = [p for p in fp + mf if len(p) > 1]
            processed_images = await process_images(
                scenes,
                scene_images,
                highlight_phonemes,
                difficulty_level,
                is_free,
                task_temp_dir,
                font_path,
                logo_path,
                illustration_style=illustration_style,  # Accessibility: CVI/BVI text overrides
            )
        else:
            # NEW LAYOUTS (picture_top, side_by_side): skip PIL text baking
            # Images are used as-is; text is rendered via HTML/CSS in the template
            # BUT we still need to download remote images to local paths
            # because WeasyPrint templates use file:// URLs for images.
            async def _download_scene_image(img: SceneImage) -> SceneImage:
                # Use cached file from validation if available
                if img.cached_path and os.path.exists(img.cached_path):
                    return SceneImage(
                        scene_id=img.scene_id,
                        image_url=f"file://{img.cached_path}",
                        prompt=img.prompt,
                        created_at=img.created_at,
                    )
                if not img.image_url.startswith("http"):
                    # Validate local images to catch corruption early
                    local_path = img.image_url.replace("file://", "")
                    if not ImageProcessor.validate_image_file(local_path):
                        logger.warning(f"[BOOK_STYLE] Local scene image is corrupt: {local_path}")
                    return img
                try:
                    local_path = await asyncio.to_thread(
                        ImageProcessor.download_image, img.image_url, task_temp_dir
                    )
                    # Pre-compress/resize to optimize WeasyPrint memory and speed
                    clean_path = local_path.replace("file://", "")
                    compressed_path = os.path.join(str(task_temp_dir), f"compressed_{os.path.basename(clean_path)}")
                    await asyncio.to_thread(
                        ImageProcessor.resize_image, local_path, compressed_path, (768, 1024)
                    )
                    local_path = f"file://{compressed_path}"
                    return SceneImage(
                        scene_id=img.scene_id,
                        image_url=local_path,
                        prompt=img.prompt,
                        created_at=img.created_at,
                    )
                except Exception as e:
                    logger.warning(f"[BOOK_STYLE] Failed to download/compress scene image {img.scene_id}, using original: {e}")
                    return img

            processed_images = list(
                await asyncio.gather(*[_download_scene_image(img) for img in scene_images])
            )

        logger.info(f"⏱️  [TIMING][pdf] Scene image processing: {_time.perf_counter() - _t_scene_proc:.2f}s")
        logger.info("Rendering PDF...")

        # Prepare template data for cover page
        cover_template_data = {
            "static_path": f"file://{static_dir.resolve()}",
            "cover_image_url": f"file://{Path(processed_cover_image.image_url).resolve()}",
            # Font variables for dynamic @font-face in cover template
            "font_family_name": font_cfg.css_family.split("'")[1] if "'" in font_cfg.css_family else "Comic Neue",
            "font_regular_path": f"file://{font_cfg.ttf_path}",
            "font_bold_path": f"file://{font_cfg.heading_ttf_path}",
            "css_font_family": font_cfg.css_family,
            "standard_codes": standard_codes or [],
            "series_info": series_info or {},
        }

        # Render the cover page
        cover_html = await html_renderer.render_template(
            "cover_page_template.html", cover_template_data
        )

        # Resolve phonemes for HTML highlighting (non-classic layouts only)
        if not layout_cfg.text_in_image:
            if highlight_text is False:
                html_highlight_phonemes = []
            else:
                fp = focus_phonemes if focus_phonemes else []
                mf = morphology_focus if morphology_focus else []
                all_multi = sorted([p for p in (fp + mf) if len(p) > 1], key=len, reverse=True)
                html_highlight_phonemes = all_multi[:3]
                # Single-letter phonemes excluded (padding per span blows out letter-spacing).
                # Capped at 3 (longest/most specific first): with 10+ phonemes the patterns
                # collectively match almost every English word, yellowing the entire page.
        else:
            html_highlight_phonemes = []

        # Render the scene pages
        scene_pages_html = []
        for i, scene in enumerate(scenes):
            # Convert newlines to spaces — CSS word-wrap handles line breaking
            scene_html_text = scene.replace("\n", " ").strip()
            # Apply phoneme highlighting for non-classic layouts
            if not layout_cfg.text_in_image and html_highlight_phonemes:
                scene_html_text = highlight_phonemes_in_html(scene_html_text, html_highlight_phonemes)
            current_processed_image = processed_images[i] if i < len(processed_images) else None
            # Resolve image URL: strip any existing file:// prefix to avoid doubling
            # (ImageProcessor.download_image returns "file://..." but we add it again below)
            raw_image_path = current_processed_image.image_url if current_processed_image else None
            if raw_image_path and raw_image_path.startswith("file://"):
                raw_image_path = raw_image_path[len("file://"):]
            # Compute layout name for font sizing
            layout_name = "side_by_side" if "side_by_side" in layout_cfg.template else "picture_top"
            scene_data = {
                "scene": scene_html_text,
                "scene_text": scene_html_text,  # For new layout templates
                "image": current_processed_image,
                "image_url_resolved": f"file://{Path(raw_image_path).resolve()}" if raw_image_path else None,
                "loop": {"index": i + 1},  # For page numbering
                "static_path": f"file://{static_dir.resolve()}",
                # Font template variables for non-classic layouts
                "font_family_name": font_cfg.css_family.split("'")[1] if "'" in font_cfg.css_family else "Comic Neue",
                "font_regular_path": f"file://{font_cfg.ttf_path}",
                "font_bold_path": f"file://{font_cfg.heading_ttf_path}",
                "css_font_family": font_cfg.css_family,
                # Dynamic font size based on text length
                "scene_font_size": compute_scene_font_size(scene_html_text, layout_name, font_cfg) if not layout_cfg.text_in_image else 24,
                "standard_codes": standard_codes or [],
            }
            scene_template_name = layout_cfg.template
            scene_html = await html_renderer.render_template(
                scene_template_name, scene_data
            )
            scene_pages_html.append(scene_html)

        # Prepare all HTML pages
        all_html_pages = [cover_html] + scene_pages_html
        
        # ── FREE BOOK WATERMARK ──────────────────────────────────────────
        # Inject prominent watermarks into every scene page for free books.
        # Top bar, bottom bar, and diagonal "FREE COPY" overlay.
        if is_free:
            # ── Top bar watermark ──
            watermark_top_html = '''
            <div style="
                position: fixed;
                top: 6px;
                left: 0;
                right: 0;
                text-align: center;
                font-family: 'Lexie Readable', Arial, sans-serif;
                font-size: 11px;
                font-weight: bold;
                color: rgba(0, 0, 0, 0.40);
                letter-spacing: 0.5px;
                z-index: 9999;
                pointer-events: none;
            ">
                FREE SAMPLE &mdash; phonicsmaker.com
            </div>
            '''
            # ── Bottom bar watermark ──
            watermark_bottom_html = '''
            <div style="
                position: fixed;
                bottom: 8px;
                left: 0;
                right: 0;
                text-align: center;
                font-family: 'Lexie Readable', Arial, sans-serif;
                font-size: 13px;
                font-weight: bold;
                color: rgba(0, 0, 0, 0.55);
                letter-spacing: 0.5px;
                z-index: 9999;
                pointer-events: none;
            ">
                Made with PhonicsMaker &mdash; Upgrade for watermark-free books &rarr; phonicsmaker.com
            </div>
            '''
            # ── Diagonal "FREE COPY" overlay ──
            watermark_diagonal_html = '''
            <div style="
                position: fixed;
                top: 50%;
                left: 50%;
                transform: translate(-50%, -50%) rotate(-35deg);
                font-family: Arial, sans-serif;
                font-size: 80px;
                font-weight: 900;
                color: rgba(0, 0, 0, 0.06);
                letter-spacing: 12px;
                white-space: nowrap;
                z-index: 9998;
                pointer-events: none;
            ">
                FREE COPY
            </div>
            '''
            combined_watermark = watermark_top_html + watermark_bottom_html + watermark_diagonal_html
            
            # ── Progressive blur config for last N pages ──
            # Pages get progressively blurrier to create upgrade pressure
            BLUR_LAST_N = 7  # Blur the last 7 scene pages
            total_scenes = len(scene_pages_html)
            blur_start_index = max(0, total_scenes - BLUR_LAST_N)  # 0-indexed
            
            # Blur levels: gentle → heavy across the last 7 pages
            blur_levels = [2, 4, 6, 8, 12, 16, 20]
            
            # Inject watermark + progressive blur into scene pages
            watermarked_scene_pages = []
            for page_idx, page_html in enumerate(scene_pages_html):
                # Always add watermarks
                extra_html = combined_watermark
                
                # Apply progressive blur to the last N pages
                if page_idx >= blur_start_index:
                    blur_step = page_idx - blur_start_index  # 0, 1, 2, ... 6
                    blur_px = blur_levels[min(blur_step, len(blur_levels) - 1)]
                    is_final_page = (page_idx == total_scenes - 1)
                    
                    # CSS to blur the entire page content
                    blur_style = f'''
                    <style>
                        body > *:not(.pm-upgrade-overlay):not(.pm-watermark) {{
                            filter: blur({blur_px}px) !important;
                            -webkit-filter: blur({blur_px}px) !important;
                        }}
                    </style>
                    '''
                    
                    if is_final_page:
                        # Final page: heavy blur + full upgrade CTA
                        upgrade_overlay = '''
                        <div class="pm-upgrade-overlay" style="
                            position: fixed;
                            top: 0; left: 0; right: 0; bottom: 0;
                            display: flex;
                            flex-direction: column;
                            align-items: center;
                            justify-content: center;
                            z-index: 10000;
                            background: rgba(255, 255, 255, 0.7);
                            text-align: center;
                            padding: 40px;
                        ">
                            <div style="font-size: 48px; margin-bottom: 16px;">🔒</div>
                            <div style="
                                font-family: 'Lexie Readable', Arial, sans-serif;
                                font-size: 28px;
                                font-weight: 900;
                                color: #1a1a2e;
                                margin-bottom: 12px;
                                line-height: 1.2;
                            ">Want to read the full story?</div>
                            <div style="
                                font-family: 'Lexie Readable', Arial, sans-serif;
                                font-size: 16px;
                                color: #4a4a6a;
                                margin-bottom: 24px;
                                max-width: 400px;
                            ">Upgrade to PhonicsMaker Pro for unlimited crystal-clear books, 17+ art styles, audio narration &amp; 21 worksheets.</div>
                            <div style="
                                display: inline-block;
                                background: linear-gradient(135deg, #8b5cf6 0%, #6d28d9 100%);
                                color: white;
                                font-family: 'Lexie Readable', Arial, sans-serif;
                                font-size: 18px;
                                font-weight: 800;
                                padding: 14px 32px;
                                border-radius: 12px;
                                letter-spacing: 0.5px;
                            ">Start Free Trial &rarr; phonicsmaker.com</div>
                        </div>
                        '''
                    else:
                        # Intermediate blurred pages: smaller upgrade hint
                        pages_remaining = total_scenes - page_idx
                        upgrade_overlay = f'''
                        <div class="pm-upgrade-overlay" style="
                            position: fixed;
                            bottom: 40px;
                            left: 50%;
                            transform: translateX(-50%);
                            z-index: 10000;
                            text-align: center;
                            padding: 12px 24px;
                            background: rgba(139, 92, 246, 0.9);
                            border-radius: 12px;
                            box-shadow: 0 4px 20px rgba(0,0,0,0.2);
                        ">
                            <div style="
                                font-family: 'Lexie Readable', Arial, sans-serif;
                                font-size: 14px;
                                font-weight: 700;
                                color: white;
                            ">🔒 {pages_remaining} pages remaining &mdash; Upgrade to unlock the full story!</div>
                        </div>
                        '''
                    
                    extra_html = blur_style + combined_watermark + upgrade_overlay
                
                # Inject into page HTML
                if '</body>' in page_html:
                    page_html = page_html.replace('</body>', f'{extra_html}</body>')
                else:
                    page_html += extra_html
                watermarked_scene_pages.append(page_html)
            
            all_html_pages = [cover_html] + watermarked_scene_pages
            logger.info(f"🔖 Injected watermark into {len(watermarked_scene_pages)} scene pages (free book), blur starts at page {blur_start_index + 1}")
        # ── END FREE BOOK WATERMARK ──────────────────────────────────────
        
        # Track book-only pages (everything except worksheets)
        # Use watermarked pages for free books
        book_scene_pages = watermarked_scene_pages if is_free else scene_pages_html
        book_html_pages = [cover_html] + book_scene_pages
        
        # Track activity pages separately for worksheets-only PDF
        activity_html_pages = []
        
        # Track page number for activities (after cover + scenes)
        current_page_num = len(scenes) + 1  # +1 for cover
        
        # ═══════════════════════════════════════════════════════════════
        # ACTIVITY PAGES - End-of-book worksheets for phonics reinforcement
        # ═══════════════════════════════════════════════════════════════
        if include_activities and not is_free:
            _t_activities = _time.perf_counter()

            if pre_rendered_activities_html:
                for html_page in pre_rendered_activities_html:
                    all_html_pages.append(html_page)
                    activity_html_pages.append(html_page)
                    current_page_num += 1
                logger.info(f"Using {len(pre_rendered_activities_html)} pre-rendered activity HTML pages from frontend editor")
                activities = []  # nothing left to template-render below
                answer_key = None
            elif pre_generated_activities:
                # Reuse activities already generated in story_tasks.py
                activities, answer_key = pre_generated_activities
                if isinstance(answer_key, dict):
                    from app.phonics_maker.activity_generation.activity_types import AnswerKeyData
                    answer_key = AnswerKeyData(**answer_key)
                logger.info(f"Using pre-generated activities ({len(activities)} activities), skipping regeneration")
            else:
                logger.info(f"Generating activity pages for phonemes: {phonemes}")

                # Use default config if not provided
                if activity_config is None:
                    activity_config = ActivityConfig()

                # Initialize activity service and generate activities
                # Use focus_phonemes (teaching targets) for worksheets when available.
                # This prevents dumping 40+ phonemes into instructions/teacher tips.
                # HARD CAP: Never pass more than 5 phonemes to activities, regardless
                # of source. More than 5 breaks Sound Matching layout and creates
                # a wall-of-text in Word Hunt / teacher tips.
                MAX_ACTIVITY_PHONEMES = 5
                activity_phonemes = focus_phonemes if focus_phonemes else None
                if not activity_phonemes:
                    # Fallback: prefer multi-letter phonemes (digraphs), then limit
                    digraphs = [p for p in phonemes if len(p) >= 2]
                    activity_phonemes = digraphs[:MAX_ACTIVITY_PHONEMES] if digraphs else phonemes[:MAX_ACTIVITY_PHONEMES]
                elif len(activity_phonemes) > MAX_ACTIVITY_PHONEMES:
                    # Even explicit focus_phonemes get capped — worksheets can't
                    # sensibly display more than 5 target sounds
                    logger.info(f"Capping {len(activity_phonemes)} focus phonemes to {MAX_ACTIVITY_PHONEMES} for activities")
                    # Prefer digraphs/long phonemes (more pedagogically useful) then take first N
                    multi = [p for p in activity_phonemes if len(p) >= 2]
                    single = [p for p in activity_phonemes if len(p) < 2]
                    activity_phonemes = (multi + single)[:MAX_ACTIVITY_PHONEMES]
                logger.info(f"Activity phonemes (from {'focus' if focus_phonemes else 'fallback'}): {activity_phonemes}")

                activity_service = ActivityService()
                activities, answer_key = await activity_service.generate_all_activities(
                    scenes=scenes,
                    phonemes=activity_phonemes,
                    config=activity_config,
                    max_phonemes=5,  # Cap for storybook worksheets only
                    story_title=story_title,
                    difficulty_level=difficulty_level.value if hasattr(difficulty_level, 'value') else difficulty_level,
                )
            
            # Activity template mapping
            activity_templates = {
                "word_hunt": "activities/activity_word_hunt.html",
                "sound_matching": "activities/activity_sound_matching.html",
                "fill_in_blank": "activities/activity_fill_blank.html",
                "tracing": "activities/activity_tracing.html",
                "circle_sound": "activities/activity_circle_sound.html",
                "word_scramble": "activities/activity_word_scramble.html",
                "cut_and_sort": "activities/activity_cut_and_sort.html",
                "sentence_building": "activities/activity_sentence_building.html",
                "phoneme_spotter": "activities/activity_phoneme_spotter.html",
                "rhyming_pairs": "activities/activity_rhyming_pairs.html",
                "phoneme_position": "activities/activity_phoneme_position.html",
                "sound_swap": "activities/activity_sound_swap.html",
                "syllable_count": "activities/activity_syllable_count.html",
                "word_ladder": "activities/activity_word_ladder.html",
                "read_and_draw": "activities/activity_read_and_draw.html",
                "phoneme_count": "activities/activity_phoneme_count.html",
                "odd_one_out": "activities/activity_odd_one_out.html",
                "missing_sound": "activities/activity_missing_sound.html",
                "real_or_nonsense": "activities/activity_real_or_nonsense.html",
                "word_building": "activities/activity_word_building.html",
                "crossword": "activities/activity_crossword.html",
                "comprehension_questions": "activities/activity_comprehension_questions.html",
                "vocabulary_building": "activities/activity_vocabulary_building.html",
                "synonyms": "activities/activity_synonyms.html",
                "inferred_meaning": "activities/activity_inferred_meaning.html",
            }
            
            # Render each activity page
            for activity_data in activities:
                activity_type = activity_data.get("activity_type")
                template_name = activity_templates.get(activity_type)
                
                if template_name:
                    current_page_num += 1
                    activity_data["page_number"] = current_page_num
                    activity_data["static_path"] = f"file://{static_dir.resolve()}"
                    
                    try:
                        activity_html = await html_renderer.render_template(
                            template_name, activity_data
                        )
                        all_html_pages.append(activity_html)
                        activity_html_pages.append(activity_html)
                        logger.info(f"Added activity page: {activity_type} (page {current_page_num})")
                    except Exception as e:
                        logger.error(f"Failed to render {activity_type} activity: {str(e)}")
                        # Continue with other activities if one fails
            
            # Render answer key page (always last activity page)
            if activities:  # Only add answer key if we have activities
                current_page_num += 1
                answer_key_data = answer_key.to_template_data()
                answer_key_data["page_number"] = current_page_num
                answer_key_data["static_path"] = f"file://{static_dir.resolve()}"
                
                try:
                    answer_key_html = await html_renderer.render_template(
                        "activities/activity_answer_key.html", answer_key_data
                    )
                    all_html_pages.append(answer_key_html)
                    activity_html_pages.append(answer_key_html)
                    logger.info(f"Added answer key page (page {current_page_num})")
                except Exception as e:
                    logger.error(f"Failed to render answer key: {str(e)}")
            logger.info(f"⏱️  [TIMING][pdf] Activity generation + render: {_time.perf_counter() - _t_activities:.2f}s")
        
        # ═══════════════════════════════════════════════════════════════

        # ═══════════════════════════════════════════════════════════════
        # AUDIO NARRATION - Generate MP3s + QR code back cover
        # ═══════════════════════════════════════════════════════════════
        audio_manifest = None
        if include_audio and not is_free:
            try:
                logger.info(f"🎙️ Generating audio narration for {len(scenes)} scenes...")
                
                if audio_config is None:
                    audio_config = AudioConfig()
                
                # Map language variant to audio locale for accent-specific voice selection
                if language_variant:
                    lv = language_variant.upper() if isinstance(language_variant, str) else str(language_variant)
                    locale_map = {
                        "US": "en_us",
                        "UK": "en_gb",
                        "AU": "en_au",
                        "NZ": "en_nz",
                        "CA": "en_ca",
                        "FR": "fr",
                        "ES": "es",
                    }
                    audio_config.locale = locale_map.get(lv, "en_us")
                
                # Try to auto-create a share record to get a short URL for the QR code
                share_url = None
                try:
                    import httpx
                    frontend_base = settings.AUDIO_PUBLIC_BASE_URL  # e.g. http://localhost:3002 or https://phonicsmaker.com
                    async with httpx.AsyncClient(timeout=10.0) as client:
                        share_res = await client.post(
                            f"{frontend_base}/api/share",
                            json={
                                "taskId": story_id,
                                "title": story_title,
                                "phonemes": phonemes,
                            },
                        )
                        if share_res.status_code == 200:
                            share_data = share_res.json()
                            share_url = share_data.get("shareUrl")
                            logger.info(f"🔗 Auto-created share link: {share_url}")
                        else:
                            logger.warning(f"Share API returned {share_res.status_code}, falling back to /listen URL")
                except Exception as share_err:
                    logger.warning(f"Could not auto-create share link (non-fatal): {share_err}")
                
                audio_service = AudioService(config=audio_config)
                audio_manifest = await audio_service.generate_book_audio(
                    book_id=story_id,
                    title=story_title,
                    scenes=scenes,
                    phonemes=phonemes,
                    temp_dir=task_temp_dir / "audio",
                    share_url=share_url,
                )
                
                # Render the back cover with QR code
                if audio_manifest and audio_manifest.qr_code_path:
                    current_page_num += 1
                    back_cover_data = audio_manifest.to_template_data()
                    back_cover_data["page_number"] = current_page_num
                    back_cover_data["static_path"] = f"file://{static_dir.resolve()}"
                    back_cover_data["qr_code_path"] = f"file://{Path(audio_manifest.qr_code_path).resolve()}"
                    
                    back_cover_html = await html_renderer.render_template(
                        "back_cover_audio.html", back_cover_data
                    )
                    all_html_pages.append(back_cover_html)
                    book_html_pages.append(back_cover_html)  # Audio back cover is part of the book, not worksheets
                    logger.info(f"📱 Added audio back cover page (page {current_page_num})")
                    
            except Exception as audio_err:
                logger.error(f"Audio generation failed (non-fatal): {audio_err}")
                # Audio failure should NOT prevent the PDF from being generated
        
        # ═══════════════════════════════════════════════════════════════

        # Add trial page for free versions
        if is_free:
            # Prepare template data for the trial page
            trial_template_data = {
                "trial_image_path": f"file://{Path(trial_image_path).resolve()}",
                "page_no": len(scenes)+1,
            }

            # Render the trial page
            trial_html = await html_renderer.render_template(
                "trial_page_template.html", trial_template_data
            )
            all_html_pages.append(trial_html)
            book_html_pages.append(trial_html)  # Trial page is part of the book

        # Clean the title to make it filesystem-safe
        safe_title = make_filesystem_safe(story_title)
        
        # Generate combined PDF (book + worksheets) into the task_temp_dir
        t_pdf_start = _time.perf_counter()
        pdf_file_path = await generate_pdf_from_html_pages(
            all_html_pages, safe_title, task_temp_dir,
            with_print_variant=with_print_variant
        )
        logger.info(f"⏱️  [TIMING] Combined PDF render: {_time.perf_counter() - t_pdf_start:.2f}s")

        pdf_compressed_path = str(task_temp_dir / f"{safe_title}{PRINT_VARIANT_SUFFIX}.pdf")
        if not os.path.exists(pdf_compressed_path):
            pdf_compressed_path = None
        
        # ── OPTIMISATION: Split secondary PDFs from the combined PDF ───────
        # Instead of re-rendering pages through WeasyPrint (which takes ~10-20s
        # for 4 sequential renders), we split the already-rendered combined PDF
        # into page-range sub-documents using pypdfium2 (< 0.5s total).
        book_only_pdf_path = None
        worksheets_pdf_path = None
        homework_pdf_path = None
        answer_key_pdf_path = None

        if activity_html_pages:
            t_split_start = _time.perf_counter()
            try:
                import pypdfium2 as pdfium

                # Page indices in the combined PDF:
                #   [0 .. len(book_html_pages)-1] = book pages (cover + scenes + optional audio back cover + trial)
                #   [len(book_html_pages) .. end]  = activity pages (worksheets + answer key)
                n_book = len(book_html_pages)
                n_total = len(all_html_pages)
                n_activities = len(activity_html_pages)

                def _split_pdf(src_path: str, page_start: int, page_end: int, suffix: str, label: str):
                    """Extract pages [page_start, page_end) from src PDF and save as a new file."""
                    try:
                        src_doc = pdfium.PdfDocument(src_path)
                        new_doc = pdfium.PdfDocument.new()
                        new_doc.import_pages(src_doc, list(range(page_start, page_end)))
                        out_path = task_temp_dir / f"{safe_title}_{suffix}.pdf"
                        new_doc.save(str(out_path))
                        new_doc.close()
                        src_doc.close()
                        logger.info(f"{label} PDF split: pages {page_start+1}-{page_end} → {out_path}")
                        return str(out_path)
                    except Exception as e:
                        logger.error(f"Failed to split {label} PDF (non-fatal): {e}")
                        return None

                # Book-only: pages 0 .. n_book-1
                book_only_pdf_path = await asyncio.to_thread(
                    _split_pdf, pdf_file_path, 0, n_book, "book_only", "Book-only"
                )

                # Worksheets (all activities + answer key): pages n_book .. n_total-1
                worksheets_pdf_path = await asyncio.to_thread(
                    _split_pdf, pdf_file_path, n_book, n_total, "worksheets", "Worksheets"
                )

                # Homework = worksheets without answer key
                if n_activities > 1:
                    homework_pdf_path = await asyncio.to_thread(
                        _split_pdf, pdf_file_path, n_book, n_total - 1, "homework", "Homework pack"
                    )

                # Answer key only (last activity page)
                answer_key_pdf_path = await asyncio.to_thread(
                    _split_pdf, pdf_file_path, n_total - 1, n_total, "answer_key", "Answer key"
                )

                logger.info(f"⏱️  [TIMING] PDF split (4 sub-PDFs): {_time.perf_counter() - t_split_start:.2f}s")

            except ImportError:
                logger.warning("pypdfium2 not available, falling back to sequential WeasyPrint re-render")
                # Fallback: re-render each sub-PDF (slow but safe)
                async def _gen_pdf(pages, suffix, label):
                    try:
                        filename = f"{safe_title}_{suffix}"
                        path = await generate_pdf_from_html_pages(pages, filename, task_temp_dir)
                        logger.info(f"{label} PDF generated: {path}")
                        return path
                    except Exception as e:
                        logger.error(f"Failed to generate {label} PDF (non-fatal): {e}")
                        return None

                book_only_pdf_path = await _gen_pdf(book_html_pages, "book_only", "Book-only")
                worksheets_pdf_path = await _gen_pdf(activity_html_pages, "worksheets", "Worksheets")
                if len(activity_html_pages) > 1:
                    homework_pdf_path = await _gen_pdf(activity_html_pages[:-1], "homework", "Homework pack")
                answer_key_pdf_path = await _gen_pdf([activity_html_pages[-1]], "answer_key", "Answer key")


        # ═══════════════════════════════════════════════════════════════
        # POWERPOINT GENERATION - Full-bleed image-per-slide for smartboards
        # Includes: cover + scene images + worksheet pages + answer key
        # ═══════════════════════════════════════════════════════════════
        pptx_local_path = None
        try:
            # Collect all book page image paths (cover + scenes)
            pptx_image_paths = []
            if processed_cover_image and processed_cover_image.image_url:
                pptx_image_paths.append(processed_cover_image.image_url)
            for img in processed_images:
                if img and img.image_url:
                    pptx_image_paths.append(img.image_url)

            # ── Render HTML-only pages (worksheets, answer key, audio back
            # cover) as PNG images so they can be included in the PPTX.
            # Flow: HTML → WeasyPrint (in-memory PDF) → pypdfium2 → PNG
            html_pages_for_pptx = list(activity_html_pages)  # worksheets + answer key
            if html_pages_for_pptx:
                try:
                    import pypdfium2 as pdfium
                    from weasyprint import HTML as WpHTML

                    for idx, page_html in enumerate(html_pages_for_pptx):
                        try:
                            # Render single HTML page to PDF bytes in memory
                            pdf_bytes = WpHTML(string=page_html).write_pdf()
                            # Convert PDF page to PNG via pypdfium2
                            pdf_doc = pdfium.PdfDocument(io.BytesIO(pdf_bytes))
                            pdf_page = pdf_doc.get_page(0)
                            bitmap = pdf_page.render(scale=2)  # 2× for crisp slides
                            pil_image = bitmap.to_pil()
                            png_path = task_temp_dir / f"pptx_worksheet_{idx}.png"
                            pil_image.save(str(png_path), "PNG")
                            pptx_image_paths.append(str(png_path))
                            logger.debug(f"PPTX: Rendered worksheet page {idx + 1} as PNG")
                            pdf_page.close()
                            pdf_doc.close()
                        except Exception as render_err:
                            logger.warning(f"PPTX: Failed to render worksheet page {idx + 1} (skipping): {render_err}")
                    logger.info(f"PPTX: Rendered {len(html_pages_for_pptx)} worksheet pages as PNGs")
                except ImportError:
                    logger.warning("PPTX: pypdfium2 not installed — worksheet pages will be excluded from PPTX")

            if pptx_image_paths:
                pptx_local_path = await generate_pptx_from_images(
                    pptx_image_paths, f"{safe_title}_smartboard", task_temp_dir
                )
                logger.info(f"PPTX generated with {len(pptx_image_paths)} slides: {pptx_local_path}")
        except Exception as pptx_err:
            logger.error(f"PPTX generation failed (non-fatal): {pptx_err}")
            # PPTX failure should NOT prevent the PDF from being generated

        # Generate thumbnail from the processed cover image
        thumbnail_local_path = None
        if processed_cover_image.image_url and os.path.exists(processed_cover_image.image_url):
            try:
                thumbnail_filename = f"thumbnail_{story_id}.jpg"
                thumbnail_output_path = task_temp_dir / thumbnail_filename
                ImageProcessor.resize_image(
                    source_path=processed_cover_image.image_url, # This is already a local path
                    output_path=str(thumbnail_output_path),
                    size=(200, 266) # Example size: width=200, height proportional for 768x1024
                )
                thumbnail_local_path = str(thumbnail_output_path)
                logger.info(f"Thumbnail generated successfully: {thumbnail_local_path}")
            except Exception as thumb_e:
                logger.error(f"Error generating thumbnail for story {story_id}: {str(thumb_e)}")
                # Continue without thumbnail if generation fails

        pdf_response = PDFGenerationResponse(
            story_id=story_id,
            pdf_url=pdf_file_path, # Local path to combined PDF
            pdf_compressed_url=pdf_compressed_path, # Local path to print-friendly PDF (may be None)
            book_only_pdf_url=book_only_pdf_path, # Local path to book-only PDF
            worksheets_pdf_url=worksheets_pdf_path, # Local path to worksheets-only PDF
            homework_pdf_url=homework_pdf_path, # Worksheets without answer key (student take-home)
            answer_key_pdf_url=answer_key_pdf_path, # Answer key only (teacher copy)
            pptx_url=pptx_local_path, # PowerPoint for smartboard display
            thumbnail_local_path=thumbnail_local_path, # Local path to thumbnail
            created_at=str(datetime.now().isoformat()),
        )
        
        # Attach audio manifest to response if generated
        if audio_manifest:
            pdf_response.audio_manifest = audio_manifest.to_dict()

        # Do NOT clean up task_temp_dir here. story_tasks.py will handle it.
        # cleanup_task_temp_dir(task_temp_dir) # Removed

        logger.info(f"PDF and thumbnail (if any) generated locally for story {story_id}")

        return pdf_response

    except Exception as e:
        logger.error(f"Error generating PDF: {str(e)}")
        raise e