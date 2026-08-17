# core/image_generation/image_service.py

from typing import List, Optional, Tuple
import asyncio
import hashlib
import io
import time
from app.core.config.logger import logger
from app.core.config.config import settings
from app.core.ai.ai_config import ai_config, RunwareSafetyBlockError
from app.core.ai.prompts import (
    COVER_IMAGE_PROMPT_GENERATION_PROMPT,
    CHARACTER_REFERENCE_PROMPT,
    CHARACTER_DESCRIPTION_EXTRACTION_PROMPT,
    get_interest_age_config,
)
from app.db.models.image import SceneImage


_CHANGE_MARKER = "\n\nRequested change:"


def parse_character_descriptions(
    block: Optional[str],
) -> Tuple[Optional[str], List[Tuple[str, str]]]:
    """Split an extracted character block into the main character's description
    and a list of (name, description) pairs for recurring secondary characters.

    The extraction prompt emits lines like::

        MAIN CHARACTER: <desc>
        SECONDARY CHARACTER (<name>): <desc>

    Falls back to treating the whole block as the main description when those
    labels are absent (e.g. an unlabelled or inherited reference description).
    """
    if not block:
        return None, []

    main_desc: Optional[str] = None
    secondaries: List[Tuple[str, str]] = []
    for raw_line in block.splitlines():
        line = raw_line.strip()
        if not line or ":" not in line:
            continue
        upper = line.upper()
        if upper.startswith("MAIN CHARACTER"):
            main_desc = line.split(":", 1)[1].strip() or None
        elif upper.startswith("SECONDARY CHARACTER"):
            body = line.split(":", 1)[1].strip()
            name = ""
            lparen, rparen = line.find("("), line.find(")")
            if 0 <= lparen < rparen:
                name = line[lparen + 1:rparen].strip()
            if body:
                secondaries.append((name, body))

    if main_desc is None and not secondaries:
        return block.strip() or None, []
    return main_desc, secondaries


def flatten_character_descriptions(block: Optional[str]) -> Optional[str]:
    """Produce a clean, label-free description for persistence and display, so
    the raw ``MAIN CHARACTER:``/``SECONDARY CHARACTER (name):`` scaffolding never
    leaks to the frontend or a reused reference book."""
    main_desc, secondaries = parse_character_descriptions(block)
    parts: List[str] = []
    if main_desc:
        parts.append(main_desc)
    for name, desc in secondaries:
        parts.append(f"{name}: {desc}" if name else desc)
    if parts:
        return " ".join(parts)
    return block.strip() if block else None


async def rewrite_prompt_with_change(base_prompt: str, change_request: str) -> str:
    instruction = (
        f"Rewrite the following image generation prompt to incorporate this change: "
        f'"{change_request}". '
        f"Return only the rewritten prompt with no explanation. "
        f"Keep the same scene, characters, and illustration style, but apply the change naturally.\n\n"
        f"Original prompt:\n{base_prompt}"
    )
    try:
        rewritten = await ai_config.generate_with_gemini(instruction)
        return rewritten.strip() or base_prompt
    except Exception as e:
        logger.error(f"Failed to rewrite prompt with Gemini: {e}", exc_info=True)
        return base_prompt


class ImageService:
    def __init__(self):
        # ACE++ configuration
        self.use_ace_plus_plus = False  # Disabled: prompt-driven consistency works well, ACE++ adds latency & timeout risk
        self.repainting_scale = 0.3  # Lower = stronger identity preservation
        self.task_type = "portrait"  # Face/character consistency ("subject" is for objects/logos)
        self._book_seed: int | None = None  # Deterministic seed for character consistency
        self._character_description: str | None = None  # Resolved canonical character description (for reuse as a reference book)

    # ── Illustration style prompt fragments ────────────────────────────
    STYLE_PROMPT_FRAGMENTS = {
        "vivid_cartoon": "Vivid cartoon style, bright saturated colors, Disney-Pixar inspired, bold outlines, smooth shading, adorable characters with big expressive eyes, children's book illustration.",
        "soft_watercolor": "Soft watercolor painting style, gentle pastel washes, delicate brush strokes, classic storybook feel, dreamy muted tones, organic textures, elegant and calming, children's book illustration.",
        "pencil_sketch": "Black and white pencil sketch style, hand-drawn look, cross-hatching, fine line work, detailed graphite illustration, classic book illustration.",
        "nordic_warm": "Warm Scandinavian children's book illustration, earthy color palette of sage green, warm terracotta, soft mustard, and cream. Hand-painted gouache texture, clean compositions, gentle characters with rosy cheeks, botanical accents, modern minimalist background design, cosy and inviting atmosphere. Premium children's book illustration.",
        "dreamy_painterly": "Dreamy painterly children's book illustration style, rich oil paint textures, warm golden lighting, deep atmospheric blues and warm amber tones. Oliver Jeffers inspired, emotionally warm characters, slightly whimsical proportions, beautiful compositions with dramatic lighting, award-winning picture book quality. Premium children's book illustration.",
        "claymation": "3D claymation style, plasticine clay texture, stop-motion animation feel, rounded sculpted characters, soft lighting, tactile handmade quality, children's book illustration.",
        "paper_collage": "Paper collage art style, torn paper textures, layered cut-out shapes, vibrant hand-painted paper pieces, bold colors, textured mixed media, children's book illustration.",
        "bold_folk": "Bold folk art children's book illustration, flat vibrant colors, decorative patterns, geometric shapes with organic warmth, Scandinavian folk art inspired, hand-printed texture feel, bold red, teal, mustard and navy color palette, playful and stimulating, modern children's book illustration.",
        "heritage_ink": "Classic heritage children's book illustration, fine ink linework with soft watercolor washes, Beatrix Potter and Shirley Hughes inspired, gentle muted color palette with warm earth tones, delicate botanical details, cross-hatched textures, timeless storybook quality, literary and elegant. Premium children's book illustration.",
        "bright_inclusive": "Modern contemporary children's book illustration, clean and bright style, bold pops of coral, teal, and sunny yellow against warm backgrounds, diverse characters with varied skin tones and features, simple confident shapes, inclusive and joyful, contemporary picture book aesthetic. Premium children's book illustration.",
        "retro_cartoon": "Classic hand-drawn cartoon children's book illustration, old school cartoon style, slightly imperfect charming ink outlines with warm flat color fills, wobbly hand-drawn linework, retro storybook feel, simple expressive faces, cheerful and nostalgic, vintage children's picture book cartoon aesthetic from the golden era. Warm earthy color palette, playful and endearing. Children's book illustration.",
        "bw_clipart": "Black-and-white clipart illustration, clean thin outlines on a pure white background, simple friendly shapes, no shading no fills no gradients, crisp linework perfect for photocopying, colouring-in ready, affordable mono printing optimised, charming minimal line-drawn characters, children's book illustration.",
        # ── Teen / Secondary School Styles ────────────────────────────
        "comic_book": "Bold comic book illustration style, strong ink outlines, dynamic panel composition, vibrant pop colors, action poses, manga and Marvel inspired, graphic novel quality, stylish and energetic, teen young-adult book illustration.",
        "modern_line_art": "Modern line art illustration style, clean single-weight linework, minimalist editorial aesthetic, confident strokes, trendy contemporary illustration, subtle colour accents, sophisticated and stylish, teen young-adult book illustration.",
        "watercolour_realism": "Realistic watercolour illustration style, atmospheric washes, moody and expressive, rich pigment blending, dramatic light and shadow, mature artistic composition, fine art quality, evocative and contemplative, teen young-adult book illustration.",
        "retro_pixel": "Retro pixel art illustration style, 16-bit video game aesthetic, crisp pixel characters, vibrant saturated palette, nostalgic gaming vibes, clean pixel grid, charming and detailed sprite art, teen young-adult book illustration.",
        "cyberpunk": "Cyberpunk illustration style, neon-lit atmosphere, electric blues and hot pinks, futuristic cityscapes, high-tech low-life aesthetic, dramatic lighting with glow effects, digital painting quality, edgy and immersive, teen young-adult book illustration.",
        # ── Accessibility / Specialist Styles ─────────────────────────
        "high_contrast": (
            "High contrast children's book illustration optimised for cortical visual impairment (CVI). "
            "STRICT RULES: Pure white or warm cream background ONLY. ONE single main object or character per scene, "
            "occupying at least 60 percent of the frame. Bold solid black outlines of 3-4 pixel thickness on every shape. "
            "Flat solid colour fills ONLY — maximum 3-4 bright saturated primary colours per scene (red, blue, yellow, green). "
            "Absolute zero visual clutter — no patterns, no textures, no gradients, no shadows, no background details. "
            "Strong figure-ground separation with clear silhouette edges. Simple geometric shapes. "
            "No overlapping elements. No depth-of-field effects. Children's book illustration."
        ),
        "simplified_shapes": (
            "Simplified geometric children's book illustration optimised for visual accessibility CVI/BVI. "
            "STRICT RULES: Single isolated object against a plain solid-colour background per scene. "
            "Basic geometric shapes only — circles, squares, rounded rectangles. Minimal detail on objects. "
            "Bold black outlines of 4 pixel thickness. Maximum 3 bright saturated colours per scene. "
            "Large clear focal point centred in frame. No distracting textures, no patterns, no gradients. "
            "No background objects or scenery. Pure flat fills. Maximum visual clarity. Children's book illustration."
        ),
        "large_print_friendly": (
            "Clean accessible children's book illustration designed for low vision readers. "
            "STRICT RULES: Generous negative space around all subjects — at least 30 percent of frame is empty. "
            "Simple uncluttered compositions with 1-2 main objects maximum. Warm and friendly characters "
            "with clear facial expressions and bold outlines. High colour contrast between subject and background. "
            "No small or intricate details — all visual elements should be clearly distinguishable at arm's length. "
            "Soft solid backgrounds in light pastels. No busy patterns or textures. "
            "Welcoming, inclusive, and visually calm. Children's book illustration."
        ),
    }
    DEFAULT_STYLE_FRAGMENT = "Cartoonish. Vibrant children's book illustration style."

    # ── Gemini prompt instructions per style ─────────────────────────────
    # These tell Gemini HOW to write the image prompt for each style.
    # They replace the hardcoded "vibrant cartoonish" instructions.
    STYLE_GEMINI_INSTRUCTIONS = {
        "vivid_cartoon": "Always describe the scenes using a single, vibrant cartoonish painting style. Use 'Cartoonish' words in the description. The clothing should be colorful, cartoonish, and child-friendly.",
        "soft_watercolor": "Always describe the scenes using a soft watercolor painting style with gentle pastel washes and delicate brush strokes. Use 'Watercolor' and 'pastel' words in the description. The clothing should be gentle, muted-tone, and child-friendly.",
        "pencil_sketch": "Always describe the scenes using a black and white pencil sketch style with hand-drawn cross-hatching and fine line work. Use 'Pencil sketch' words in the description. Do NOT mention any colours — describe everything in terms of shading, tone, and linework. The clothing should be simple and child-friendly.",
        "nordic_warm": "Always describe the scenes using a warm Scandinavian children's book illustration style with earthy color palette of sage green, warm terracotta, soft mustard, and cream. Use 'Scandinavian' and 'gouache' words in the description. The clothing should be cosy, natural-toned, and child-friendly.",
        "dreamy_painterly": "Always describe the scenes using a dreamy painterly children's book illustration style with rich oil paint textures, warm golden lighting, and deep atmospheric tones. Use 'Painterly' and 'dreamy' words in the description. The clothing should be warm-toned and child-friendly.",
        "claymation": "Always describe the scenes using a 3D claymation style with plasticine clay texture and stop-motion animation feel. Use 'Claymation' and 'clay' words in the description. The clothing should be simple, sculpted, and child-friendly.",
        "paper_collage": "Always describe the scenes using a paper collage art style with torn paper textures and layered cut-out shapes. Use 'Collage' and 'paper' words in the description. The clothing should be bold, textured, and child-friendly.",
        "bold_folk": "Always describe the scenes using a bold folk art children's book illustration style with flat vibrant colors and decorative patterns. Use 'Folk art' words in the description. The clothing should be decorative, bold, and child-friendly.",
        "heritage_ink": "Always describe the scenes using a classic heritage children's book illustration style with fine ink linework and soft watercolor washes. Use 'Heritage' and 'ink' words in the description. The clothing should be classic, gentle-toned, and child-friendly.",
        "bright_inclusive": "Always describe the scenes using a modern contemporary children's book illustration style with clean and bright colors. Use 'Modern' and 'contemporary' words in the description. The clothing should be bright, inclusive, and child-friendly.",
        "retro_cartoon": "Always describe the scenes using a classic hand-drawn cartoon children's book illustration style with slightly imperfect charming ink outlines, warm flat color fills, and a retro storybook feel. Use 'Retro cartoon' words in the description. The clothing should be warm-toned, nostalgic, and child-friendly.",
        "bw_clipart": "Always describe the scenes using a BLACK-AND-WHITE CLIPART style with clean thin outlines on a pure white background, simple friendly shapes, NO colour, NO shading, NO fills, NO gradients. Use 'Black-and-white clipart' words in the description. Do NOT mention ANY colours at all — everything must be described as black outlines on white. The clothing should be simple outline shapes only, described by shape not colour. This is a colouring-in style meant for mono printing.",
        "comic_book": "Always describe the scenes using a bold comic book illustration style with strong ink outlines, dynamic panel composition, and vibrant pop colors. Use 'Comic book' words in the description. The clothing should be bold, stylish, and age-appropriate.",
        "modern_line_art": "Always describe the scenes using a modern line art illustration style with clean single-weight linework and minimalist editorial aesthetic. Use 'Line art' words in the description. The clothing should be trendy, contemporary, and age-appropriate.",
        "watercolour_realism": "Always describe the scenes using a realistic watercolour illustration style with atmospheric washes and moody, expressive tones. Use 'Watercolour' and 'realistic' words in the description. The clothing should be natural, expressive, and age-appropriate.",
        "retro_pixel": "Always describe the scenes using a retro pixel art illustration style with 16-bit video game aesthetic and crisp pixel characters. Use 'Pixel art' and 'retro' words in the description. The clothing should be simple pixel designs, vibrant, and age-appropriate.",
        "cyberpunk": "Always describe the scenes using a cyberpunk illustration style with neon-lit atmosphere, electric blues and hot pinks. Use 'Cyberpunk' and 'neon' words in the description. The clothing should be futuristic, edgy, and age-appropriate.",
        # ── Accessibility / Specialist Styles ─────────────────────────
        "high_contrast": (
            "ACCESSIBILITY MODE — CVI/BVI OPTIMISED. Describe EVERY scene with these STRICT rules: "
            "1. Use 'High contrast' and 'CVI-friendly' words. "
            "2. Each scene has ONE single main subject against a PURE WHITE background. "
            "3. Describe the subject using SIMPLE GEOMETRIC SHAPES with BOLD BLACK OUTLINES. "
            "4. Use only 2-3 FLAT BRIGHT PRIMARY COLOURS per scene — no gradients, no textures, no patterns. "
            "5. NO background details, NO secondary objects, NO overlapping elements. "
            "6. The subject must fill at least 60% of the image. "
            "7. Clothing should be simple, bold solid colours, child-friendly."
        ),
        "simplified_shapes": (
            "ACCESSIBILITY MODE — CVI/BVI OPTIMISED. Describe EVERY scene with these STRICT rules: "
            "1. Use 'Simplified shapes' and 'geometric' words. "
            "2. Each scene shows ONE isolated object or character, centred in frame. "
            "3. Use BASIC SHAPES ONLY — circles, squares, triangles, rounded forms. "
            "4. PLAIN SOLID-COLOUR BACKGROUND — one single flat colour. "
            "5. Maximum 3 colours total in the entire scene. "
            "6. NO details, NO textures, NO patterns — pure flat colour fills. "
            "7. Clothing described by shape only, simple and child-friendly."
        ),
        "large_print_friendly": (
            "ACCESSIBILITY MODE — LOW VISION OPTIMISED. Describe EVERY scene with these rules: "
            "1. Use 'Clean' and 'accessible' words. "
            "2. 1-2 main objects maximum per scene with GENEROUS empty space around them. "
            "3. SOFT PASTEL solid backgrounds — no busy patterns or textures. "
            "4. Characters have CLEAR, LARGE facial expressions and bold outlines. "
            "5. NO small or intricate details — everything must be visible at arm's length. "
            "6. HIGH contrast between subject and background. "
            "7. Clothing should be simple, warm-toned, and child-friendly."
        ),
    }
    DEFAULT_GEMINI_INSTRUCTION = "Always describe the scenes using a single, vibrant cartoonish painting style. Use 'Cartoonish' words in the description. The clothing should be colorful, cartoonish, and child-friendly."

    # ── Negative prompts to reinforce style at the Runware level ──────────
    STYLE_NEGATIVE_PROMPTS = {
        "bw_clipart": "color, colorful, vibrant, saturated, gradient, shading, shadow, painted, watercolor, 3d, realistic, photographic",
        "pencil_sketch": "color, colorful, vibrant, saturated, painted, watercolor, 3d, realistic, photographic",
        # ── Accessibility — aggressively block visual clutter ──────────
        "high_contrast": (
            "gradient, texture, pattern, busy background, detailed background, shadows, soft shadows, "
            "depth of field, bokeh, multiple characters, crowd, scenery, landscape, watercolor wash, "
            "subtle colors, muted colors, pastel, faded, blurry, noise, grain, complex composition, "
            "overlapping elements, transparency, reflection, glow, lens flare, photographic, realistic"
        ),
        "simplified_shapes": (
            "gradient, texture, pattern, detailed, complex, busy, shadows, shading, depth, perspective, "
            "multiple objects, crowd, scenery, landscape, background details, watercolor, painterly, "
            "realistic, photographic, 3d, overlapping, transparency, intricate, small details, "
            "fine lines, thin lines, noise, grain"
        ),
        "large_print_friendly": (
            "busy background, detailed background, pattern, texture, small details, intricate, "
            "complex composition, multiple characters, crowd, overlapping elements, thin lines, "
            "fine details, noise, grain, blurry, low contrast, muted, faded, photographic, realistic"
        ),
    }

    # ── Accessibility style IDs ──────────────────────────────────────────
    ACCESSIBILITY_STYLES = frozenset({"high_contrast", "simplified_shapes", "large_print_friendly"})

    @classmethod
    def is_accessibility_style(cls, style_id: Optional[str]) -> bool:
        """Check if the given illustration style is an accessibility/CVI/BVI style."""
        return (style_id or "") in cls.ACCESSIBILITY_STYLES

    def _apply_illustration_style(self, prompt: str, illustration_style: Optional[str] = None) -> str:
        """Replace the default 'Cartoonish' art-style descriptor with the selected style fragment."""
        style_fragment = self.STYLE_PROMPT_FRAGMENTS.get(illustration_style or "", None)
        if not style_fragment:
            return prompt  # Keep as-is for default / unknown styles

        # Replace common default style keywords with the user-chosen style
        import re
        # Try to replace the leading "Cartoonish." or "Cartoonish" at the start of prompts
        modified = re.sub(
            r'^Cartoonish\.?\s*',
            style_fragment + " ",
            prompt,
            count=1,
        )
        if modified == prompt:
            # If no leading 'Cartoonish' was found, prepend the style fragment
            modified = style_fragment + " " + prompt

        return modified

    def get_style_gemini_instruction(self, illustration_style: Optional[str] = None) -> str:
        """Return the Gemini prompt instruction for how to describe the art style."""
        return self.STYLE_GEMINI_INSTRUCTIONS.get(
            illustration_style or "", self.DEFAULT_GEMINI_INSTRUCTION
        )

    def get_style_negative_prompt(self, illustration_style: Optional[str] = None) -> Optional[str]:
        """Return additional negative prompt text for style enforcement, or None."""
        return self.STYLE_NEGATIVE_PROMPTS.get(illustration_style or "", None)

    # ── Negative prompt applied to every structured cover image ─────────────
    COVER_NEGATIVE_PROMPT = (
        "extra text, garbled text, nonsense words, random letters, signature, watermark, logo, "
        "author name, labels, extra titles, typography, words on objects, speech bubbles, messy text"
    )

    async def validate_cover_image(
        self,
        image_url: str,
        expected_title: str,
        cover_prompt: str,
        local_path: str | None = None,
    ) -> dict:
        """
        Use Gemini Flash to check a cover image for quality issues.

        Args:
            local_path: If provided, read image bytes from this file instead of downloading.

        Returns:
            dict with keys:
                - passed (bool): True if image is acceptable
                - issues (list[str]): Description of problems found
        """
        import httpx as _httpx
        from app.core.config.config import settings as _settings

        api_key = _settings.GEMINI_API_KEY
        if not api_key:
            logger.warning("No GEMINI_API_KEY — skipping cover validation")
            return {"passed": True, "issues": []}

        # Read from local cache if available, otherwise download
        image_bytes = None
        if local_path:
            import os
            if os.path.exists(local_path):
                with open(local_path, "rb") as f:
                    image_bytes = f.read()

        if image_bytes is None:
            async with _httpx.AsyncClient(timeout=30.0) as client:
                img_resp = await client.get(image_url)
                if img_resp.status_code != 200:
                    logger.warning(f"Could not download cover image for validation: {img_resp.status_code}")
                    return {"passed": True, "issues": []}
                image_bytes = img_resp.content

        import base64
        image_b64 = base64.b64encode(image_bytes).decode("utf-8")
        # Detect mime type from first bytes
        mime_type = "image/jpeg"
        if image_bytes[:4] == b'\x89PNG':
            mime_type = "image/png"

        validation_prompt = (
            f"You are a quality checker for children's book cover images.\n\n"
            f"Expected title on the cover: \"{expected_title}\"\n"
            f"The cover prompt was: \"{cover_prompt[:500]}\"\n\n"
            f"Analyse this cover image and check for:\n"
            f"1. TEXT LEGIBILITY: Look at ALL text on the image — title, subtitle, labels, "
            f"focus sounds, etc. Every piece of text must be clearly readable and properly "
            f"formatted. Common AI image generation problems include:\n"
            f"   - Letters running together or overlapping\n"
            f"   - Characters that are distorted, malformed, or partially missing\n"
            f"   - Words where letters are jumbled, swapped, or in wrong order\n"
            f"   - Text that looks like random characters or symbols instead of real words\n"
            f"   - Commas, hyphens, or punctuation placed incorrectly between letters\n"
            f"   - Phonics notation (like 'sh', 'ch', 'igh') that is broken up or garbled\n"
            f"   If ANY text on the image is not perfectly clear and legible, fail the image.\n"
            f"2. UNEXPECTED TEXT: AI image generators often add random words, letters, or "
            f"phrases that were NOT requested in the prompt. Check for any text on the image "
            f"that does not match content from the cover prompt. If there is ANY text that "
            f"was not explicitly requested, fail the image.\n"
            f"3. MISSPELLED TITLE: If the title appears on the image, is it spelled correctly? "
            f"Compare it exactly to: \"{expected_title}\"\n"
            f"4. OVERALL QUALITY: Does the image look like a proper children's book cover "
            f"(not distorted, not missing key elements)?\n\n"
            f"Respond with ONLY valid JSON (no markdown):\n"
            f'{{"passed": true/false, "issues": ["issue1", "issue2"]}}\n'
            f"If the image is fine, return: {{\"passed\": true, \"issues\": []}}\n"
            f"Be VERY strict about text legibility. AI image generators frequently produce "
            f"text that looks roughly correct at a glance but is actually garbled on closer "
            f"inspection. Zoom in mentally on every piece of text and verify each word is "
            f"properly spelled and clearly rendered with distinct, well-formed characters."
        )

        payload = {
            "contents": [
                {
                    "role": "user",
                    "parts": [
                        {"inline_data": {"mime_type": mime_type, "data": image_b64}},
                        {"text": validation_prompt},
                    ],
                }
            ],
            "generationConfig": {
                "responseMimeType": "text/plain",
            },
        }

        api_url = (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            "gemini-3.1-flash-lite-preview:generateContent"
        )

        try:
            async with _httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    api_url,
                    json=payload,
                    headers={"x-goog-api-key": api_key, "Content-Type": "application/json"},
                )

            if resp.status_code != 200:
                logger.warning(f"Gemini vision API returned {resp.status_code} — skipping validation")
                return {"passed": True, "issues": []}

            data = resp.json()
            text = ""
            for candidate in data.get("candidates", []):
                for part in candidate.get("content", {}).get("parts", []):
                    text += part.get("text", "")

            import json
            # Strip markdown fences if present
            text = text.strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
            result = json.loads(text)
            logger.info(f"Cover validation result: {result}")
            return result

        except Exception as e:
            logger.warning(f"Cover validation failed (non-blocking): {e}")
            return {"passed": True, "issues": []}

    async def generate_cover_visual_description(
        self,
        story_title: str,
        story_idea: str,
        short_scenes: List[str],
        illustration_style: Optional[str] = None,
        student_age: Optional[str] = None,
    ) -> str:
        """
        Ask Gemini to generate a rich visual description for the cover image.

        This description is used for TWO purposes:
          1. Plugged into the Text-Strict cover prompt as [Visual Description]
          2. Passed as context to scene prompt generation & character extraction
             to maintain character consistency across the book.

        Returns 80-120 words with detailed character appearance, clothing,
        colours, action, and background.  Falls back to story_idea on error.
        """
        scenes_preview = " | ".join(short_scenes[:4])
        style_instruction = self.get_style_gemini_instruction(illustration_style)
        interest_cfg = get_interest_age_config(student_age)
        build_descriptors = interest_cfg["build_descriptors"]

        prompt = (
            f"Write a DETAILED visual description (80-120 words) for a storybook cover "
            f"aimed at {interest_cfg['image_audience']}.\n\n"
            f"Story title: {story_title}\n"
            f"Story idea: {story_idea}\n"
            f"Opening scenes: {scenes_preview}\n\n"
            f"Include ALL of the following:\n"
            f"- Main character(s): build/stature ({build_descriptors}), hair colour/style, eye colour, skin tone, "
            f"exact clothing with colours and patterns, shoes, accessories\n"
            f"- Clothing must be {interest_cfg['image_clothing']}\n"
            f"- What the character(s) are doing and feeling (action + emotion)\n"
            f"- The background/setting with specific details\n"
            f"- {style_instruction}\n\n"
            f"When describing characters, avoid stating a numeric age (e.g. '6-year-old'). "
            f"Instead convey their build through physical descriptors ({build_descriptors}).\n\n"
            f"Output ONLY the visual description, no other text. Do not mention any text, "
            f"titles, or words appearing in the image."
        )
        try:
            description = await ai_config.generate_with_gemini(prompt)
            description = description.strip().strip('"')
            if description and len(description) > 20:
                logger.info(f"Cover visual description ({len(description.split())} words): {description[:100]}...")
                return description
        except Exception as e:
            logger.warning(f"Cover visual description generation failed ({e}), using story_idea")
        return story_idea

    def build_structured_cover_prompt(
        self,
        story_title: str,
        phonemes: List[str],
        visual_description: str,
        illustration_style: Optional[str] = None,
    ) -> tuple:
        """
        Build the Text-Strict Prompt Structure Formula for the cover image.
        Title and subtitle are baked into the prompt so Runware renders them
        as part of the illustration.  Returns (positive_prompt, negative_prompt).
        """
        style_fragment = self.STYLE_PROMPT_FRAGMENTS.get(
            illustration_style or "", self.DEFAULT_STYLE_FRAGMENT
        )

        if phonemes:
            subtitle = f"Focus Sounds: {', '.join(phonemes)}"
            positive_prompt = (
                f'A children\'s phonics storybook cover titled "{story_title}" '
                f'with a small fun rounded pill-shaped badge at a slight angle containing the text "{subtitle}". '
                f'{visual_description}. '
                f'{style_fragment} '
                f'Professional children\'s book cover design, featuring only the specified title text '
                f'and the focus sounds pill badge, with absolutely no other words, text, logos, or garbled letters '
                f'present anywhere in the image.'
            )
        else:
            positive_prompt = (
                f'A children\'s storybook cover titled "{story_title}". '
                f'{visual_description}. '
                f'{style_fragment} '
                f'Professional children\'s book cover design, featuring only the specified title text '
                f'with absolutely no other words, text, logos, or garbled letters '
                f'present anywhere in the image.'
            )

        return positive_prompt, self.COVER_NEGATIVE_PROMPT

    async def _extract_character_description(
        self,
        cover_image_prompt: str,
        short_scenes: Optional[List[str]] = None,
        student_age: Optional[str] = None,
    ) -> Optional[str]:
        """
        Extract concise, canonical descriptions for the main character and any
        recurring secondary characters (e.g. a coach) from the cover image prompt
        and story scenes. This is prepended to every scene prompt to ensure
        character consistency across all illustrations.

        Returns:
            Optional[str]: The character description block, or None if extraction fails.
        """
        try:
            logger.info("Extracting canonical character description(s) for consistency...")
            interest_cfg = get_interest_age_config(student_age)
            formatted_prompt = CHARACTER_DESCRIPTION_EXTRACTION_PROMPT.format(
                cover_image_prompt=cover_image_prompt,
                story_scenes="\n".join(short_scenes or []),
                build_descriptors=interest_cfg["build_descriptors"],
                image_audience=interest_cfg["image_audience"],
            )
            description = await ai_config.generate_with_gemini(formatted_prompt)
            description = description.strip()
            
            if description and len(description) > 10:
                logger.info(f"Extracted character description: {description[:80]}...")
                return description
            else:
                logger.warning("Character description extraction returned empty/short result")
                return None
        except Exception as e:
            logger.warning(f"Failed to extract character description (non-fatal): {e}")
            return None

    async def generate_cover_image_prompt(
        self, story_idea: str, short_scenes: str, illustration_style: Optional[str] = None,
        student_age: Optional[str] = None,
    ) -> str:
        """
        Generate a prompt for the cover image using the cover detailed scene.
        Falls back to a safe generic prompt if Gemini rejects the generation.
        """
        # Resolved outside the try so the except-branch fallback can use it too.
        interest_cfg = get_interest_age_config(student_age)
        try:
            logger.info("Generating cover image prompt...")

            style_instruction = self.get_style_gemini_instruction(illustration_style)

            formatted_prompt = COVER_IMAGE_PROMPT_GENERATION_PROMPT.format(
                story_idea=story_idea,
                short_scenes="\n".join(
                    [f"{i+1}. {scene}" for i, scene in enumerate(short_scenes)]
                ),
                illustration_style_instruction=style_instruction,
                image_audience=interest_cfg["image_audience"],
                image_clothing=interest_cfg["image_clothing"],
            )

            # Call Gemini API
            image_prompt = await ai_config.image_prompt_generate_with_gemini(formatted_prompt)

            # Safety net: ensure the generated prompt ends with the anti-text suffix.
            # Even with strong instructions, LLMs sometimes omit the suffix.
            anti_text_suffix = "Absolutely no text, no letters, no words, no numbers, no writing, no titles, no labels, completely text-free illustration only."
            if anti_text_suffix.lower() not in image_prompt.lower():
                # Strip any partial/weaker suffix the LLM may have added
                import re
                image_prompt = re.sub(
                    r'\s*No text[^.]*text-free[^.]*\.?\s*$',
                    '',
                    image_prompt,
                    flags=re.IGNORECASE,
                ).strip()
                image_prompt = f"{image_prompt} {anti_text_suffix}"

            logger.info("Cover image prompt generated successfully.")

            return image_prompt

        except Exception as e:
            logger.warning(f"Cover image prompt generation failed ({e}). Using safe fallback.")
            # Build a safe fallback so the book can still generate
            style_keyword = self.STYLE_PROMPT_FRAGMENTS.get(
                illustration_style or "", self.DEFAULT_STYLE_FRAGMENT
            ).split(".")[0]
            fallback = (
                f"{style_keyword}. Medium shot, full body view. "
                f"Storybook cover illustration for {interest_cfg['image_audience']}. {story_idea}. "
                f"Expressive characters in an engaging setting, warm lighting, "
                f"vibrant colors. Clothing {interest_cfg['image_clothing']}. "
                f"No text, no letters, no words, completely text-free."
            )
            return fallback

    async def generate_character_reference_prompt(
        self, story_idea: str, cover_image_prompt: str, illustration_style: Optional[str] = None,
        student_age: Optional[str] = None,
    ) -> str:
        """
        Generate a character reference sheet prompt for ACE++ consistency.
        This creates a detailed prompt for a neutral, full-body character image
        that will be used as the reference for all subsequent scene generations.
        """
        try:
            logger.info("Generating character reference prompt for ACE++...")

            style_instruction = self.get_style_gemini_instruction(illustration_style)

            interest_cfg = get_interest_age_config(student_age)
            formatted_prompt = CHARACTER_REFERENCE_PROMPT.format(
                story_idea=story_idea,
                cover_image_prompt=cover_image_prompt,
                illustration_style_instruction=style_instruction,
                image_audience=interest_cfg["image_audience"],
                image_clothing=interest_cfg["image_clothing"],
                build_descriptors=interest_cfg["build_descriptors"],
            )

            # Call Gemini API
            character_ref_prompt = await ai_config.image_prompt_generate_with_gemini(
                formatted_prompt
            )

            logger.info("Character reference prompt generated successfully.")
            return character_ref_prompt

        except Exception as e:
            logger.error(f"Error generating character reference prompt: {str(e)}")
            raise e

    async def generate_character_reference_image(
        self, story_idea: str, cover_image_prompt: str, student_age: Optional[str] = None
    ) -> str:
        """
        Generate the character reference image for ACE++ consistency.
        This is the first step - creates a clean reference that ACE++ will use
        to maintain character identity across all scenes.
        
        Returns:
            str: URL of the generated character reference image
        """
        try:
            logger.info("Generating character reference image for ACE++...")

            # Generate the character reference prompt
            character_ref_prompt = await self.generate_character_reference_prompt(
                story_idea, cover_image_prompt, student_age=student_age
            )

            # Generate the reference image using standard generation (not ACE++)
            # This is the "seed" image that ACE++ will reference
            character_ref_url = await ai_config.generate_image(
                character_ref_prompt, 
                is_free=False  # Always high quality for reference
            )

            logger.info(f"Character reference image generated: {character_ref_url[:80]}...")
            return character_ref_url

        except Exception as e:
            logger.error(f"Error generating character reference image: {str(e)}")
            raise e

    async def generate_images(
        self,
        cover_image_prompt: str,
        scene_image_prompts: List[str],
        is_free: bool,
        story_idea: Optional[str] = None,
        illustration_style: Optional[str] = None,
        character_ref_url: Optional[str] = None,
        character_description: Optional[str] = None,
        reference_seed: Optional[int] = None,
        cover_negative_prompt: Optional[str] = None,
        cache_dir: Optional[str] = None,
        student_age: Optional[str] = None,
    ) -> List[SceneImage]:
        """
        Generate images for all scenes with ACE++ character consistency.
        
        This method uses a two-pass approach:
        1. Generate a character reference image (neutral pose, full body)
        2. Generate all scenes using ACE++ with the reference for consistency
        
        Args:
            cover_image_prompt: The prompt for the cover image
            scene_image_prompts: List of prompts for each scene
            is_free: Whether this is a free generation
            story_idea: Optional story idea for character reference generation
            illustration_style: Optional art style override (e.g. "soft_watercolor")
            character_ref_url: Pre-computed character reference image URL (from parallel generation)
            character_description: Pre-computed character description (from parallel generation, skips internal LLM call)
            reference_seed: Book seed inherited from a reference book — reuses the same noise family so
                recurring characters render consistently across books. Overrides the story-idea hash.

        Returns:
            List[SceneImage]: All generated images (cover + scenes)
        """
        # Apply illustration style to SCENE prompts only.
        # The cover uses the Text-Strict structured prompt which already
        # includes the style fragment — reapplying would double it.
        is_structured_cover = cover_negative_prompt is not None
        if illustration_style:
            logger.info(f"Applying illustration style: {illustration_style}")
            if not is_structured_cover:
                cover_image_prompt = self._apply_illustration_style(cover_image_prompt, illustration_style)
            scene_image_prompts = [
                self._apply_illustration_style(p, illustration_style)
                for p in scene_image_prompts
            ]

        # Extract canonical character description and inject into SCENE prompts.
        # The structured cover prompt must stay clean for accurate title/subtitle
        # rendering — character desc prefix would corrupt the Text-Strict formula.
        # Use pre-computed description if available, otherwise extract it now.
        if character_description is None:
            character_description = await self._extract_character_description(cover_image_prompt)
        # Remember the resolved description so callers can persist it for reuse as a reference book.
        self._character_description = character_description
        if character_description:
            main_desc, secondary_chars = parse_character_descriptions(character_description)

            def _char_prefix_for(target_prompt: str) -> str:
                # Anchor the main character everywhere, but only anchor a secondary
                # character in scenes that actually reference them by name — so a
                # coach or teacher isn't forced into every page.
                descs: List[str] = []
                if main_desc:
                    descs.append(main_desc)
                lowered = target_prompt.lower()
                for name, desc in secondary_chars:
                    if name and name.lower() in lowered:
                        descs.append(f"{name}: {desc}")
                combined = " ".join(descs) if descs else character_description
                return (
                    f"IMPORTANT - Use this EXACT character description for the characters in this scene: {combined}. "
                    f"Only depict characters who appear in this scene; do not add characters who are not present. "
                    f"NEVER change a character's species, body type, or distinctive features (such as wings, fur, tail, or ears) between pages. "
                    f"Maintain consistent colours throughout. Anatomically correct, proper anatomy, correct number of limbs. "
                )

            if not is_structured_cover:
                cover_image_prompt = _char_prefix_for(cover_image_prompt) + cover_image_prompt
            scene_image_prompts = [
                _char_prefix_for(p) + p for p in scene_image_prompts
            ]
        else:
            anatomy_prefix = "Anatomically correct, proper human anatomy, correct number of limbs. "
            if not is_structured_cover:
                cover_image_prompt = anatomy_prefix + cover_image_prompt
            scene_image_prompts = [anatomy_prefix + p for p in scene_image_prompts]
            logger.info(f"Injected character description into {len(scene_image_prompts)} scene prompts"
                        + (" (cover exempt — structured prompt)" if is_structured_cover else " + cover"))

        # Generate a deterministic seed for character consistency.
        # A reference book's seed (if provided) wins so recurring characters share the same noise
        # family across books; otherwise derive it from the story idea
        # (same story idea → same seed → same noise → more consistent characters).
        if reference_seed is not None:
            self._book_seed = int(reference_seed)
            logger.info(f"Using inherited reference seed {self._book_seed} for character consistency")
        elif story_idea:
            seed_hash = hashlib.sha256(story_idea.encode()).hexdigest()
            self._book_seed = int(seed_hash[:8], 16)  # 32-bit seed from first 8 hex chars
            logger.info(f"Using deterministic seed {self._book_seed} for character consistency")
        else:
            self._book_seed = None

        # Resolve style-specific negative prompt for Runware enforcement
        extra_negative_prompt = self.get_style_negative_prompt(illustration_style)
        if extra_negative_prompt:
            logger.info(f"Using style-specific negative prompt: {extra_negative_prompt}")

        try:
            if self.use_ace_plus_plus and story_idea:
                return await self._generate_images_with_ace(
                    cover_image_prompt,
                    scene_image_prompts,
                    is_free,
                    story_idea,
                    character_ref_url=character_ref_url,
                    extra_negative_prompt=extra_negative_prompt,
                    cover_negative_prompt=cover_negative_prompt,
                )
            else:
                return await self._generate_images_without_ace(
                    cover_image_prompt,
                    scene_image_prompts,
                    is_free,
                    extra_negative_prompt=extra_negative_prompt,
                    cover_negative_prompt=cover_negative_prompt,
                    cache_dir=cache_dir,
                )

        except Exception as e:
            logger.error(f"Error generating images: {str(e)}")
            raise e

    async def _generate_images_with_ace(
        self,
        cover_image_prompt: str,
        scene_image_prompts: List[str],
        is_free: bool,
        story_idea: str,
        character_ref_url: Optional[str] = None,
        extra_negative_prompt: Optional[str] = None,
        cover_negative_prompt: Optional[str] = None,
    ) -> List[SceneImage]:
        """
        Generate images using ACE++ for character consistency.

        Robustness features:
        - Semaphore throttles to ACE_MAX_CONCURRENT parallel API calls
        - Shared `cancelled` flag aborts queued tasks on first hard failure
        - Total batch timeout (ACE_BATCH_TIMEOUT_S) prevents infinite retries
        - return_exceptions=True prevents one failure from crashing the batch
        - Tolerates partial failures: uses ACE++ images that succeeded,
          falls back to standard gen only for the ones that failed
        - Only falls back to full standard gen if ALL ACE++ images fail
        """
        ACE_MAX_CONCURRENT = 3
        ACE_BATCH_TIMEOUT_S = 120  # seconds for entire batch

        semaphore = asyncio.Semaphore(ACE_MAX_CONCURRENT)
        cancelled = False  # shared flag — queued tasks check this before starting

        try:
            # STEP 1: Character reference image
            if character_ref_url:
                logger.info("Step 1/2: Using pre-computed character reference image.")
            else:
                logger.info("Step 1/2: Generating character reference image...")
                character_ref_url = await self.generate_character_reference_image(
                    story_idea, cover_image_prompt, student_age=student_age
                )

            # STEP 2: Generate images with ACE++ (throttled + timeout)
            total = 1 + len(scene_image_prompts)
            logger.info(f"Step 2/2: Generating {total} images with ACE++ (max {ACE_MAX_CONCURRENT} concurrent, {ACE_BATCH_TIMEOUT_S}s timeout)...")

            async def generate_one_ace(scene_id: str, prompt: str, repainting_scale: float) -> SceneImage:
                nonlocal cancelled
                # Check before waiting for semaphore
                if cancelled:
                    raise asyncio.CancelledError(f"Batch cancelled before {scene_id}")
                async with semaphore:
                    # Check again after acquiring semaphore
                    if cancelled:
                        raise asyncio.CancelledError(f"Batch cancelled before {scene_id}")
                    logger.info(f"ACE++ generating {scene_id}...")
                    url = await ai_config.generate_image_with_ace_plus_plus(
                        prompt=prompt,
                        reference_image_url=character_ref_url,
                        is_free=is_free,
                        repainting_scale=repainting_scale,
                        task_type=self.task_type,
                    )
                    logger.info(f"ACE++ completed {scene_id}.")
                    return SceneImage(
                        scene_id=scene_id,
                        image_url=url,
                        prompt=prompt,
                        created_at=self._get_current_timestamp(),
                    )

            # Build task list: cover + all scenes
            scene_ids_and_prompts = [("cover", cover_image_prompt, 0.25)] + [
                (f"scene_{i+2}", prompt, self.repainting_scale)
                for i, prompt in enumerate(scene_image_prompts)
            ]

            tasks = [
                generate_one_ace(sid, prompt, scale)
                for sid, prompt, scale in scene_ids_and_prompts
            ]

            # Run with a hard deadline — prevents infinite retry cascading
            results = await asyncio.wait_for(
                asyncio.gather(*tasks, return_exceptions=True),
                timeout=ACE_BATCH_TIMEOUT_S,
            )

            # Separate successes from failures
            successes = []
            failures = []
            failed_indices = []
            for i, result in enumerate(results):
                if isinstance(result, BaseException):
                    failures.append((i, result))
                    failed_indices.append(i)
                else:
                    successes.append(result)

            if not failures:
                logger.info(f"All {total} ACE++ images generated successfully.")
                return list(results)

            logger.warning(
                f"ACE++ partial failure: {len(successes)}/{total} succeeded, "
                f"{len(failures)} failed. Generating fallbacks for failed images..."
            )

            # If ALL failed, fall back entirely
            if not successes:
                raise Exception(f"All {total} ACE++ images failed")

            # Generate standard (non-ACE++) images for the ones that failed
            fallback_tasks = []
            for idx in failed_indices:
                sid, prompt, _ = scene_ids_and_prompts[idx]
                fallback_tasks.append(
                    self._generate_single_image_with_seed(sid, prompt, is_free, extra_negative_prompt=extra_negative_prompt)
                )

            fallback_results = await asyncio.gather(*fallback_tasks, return_exceptions=True)

            # Merge: use ACE++ successes + standard fallbacks
            merged = list(results)
            fb_idx = 0
            for idx in failed_indices:
                fb_result = fallback_results[fb_idx]
                fb_idx += 1
                if isinstance(fb_result, BaseException):
                    logger.error(f"Fallback also failed for index {idx}: {fb_result}")
                    # Use a placeholder or re-raise
                    raise fb_result
                merged[idx] = fb_result

            logger.info(f"Generated {total} images ({len(successes)} ACE++ + {len(failed_indices)} standard fallback).")
            return merged

        except asyncio.TimeoutError:
            cancelled = True
            logger.error(f"ACE++ batch timed out after {ACE_BATCH_TIMEOUT_S}s. Falling back to standard generation.")
            return await self._generate_images_without_ace(
                cover_image_prompt, scene_image_prompts, is_free,
                extra_negative_prompt=extra_negative_prompt,
                cover_negative_prompt=cover_negative_prompt,
            )
        except Exception as e:
            cancelled = True
            logger.error(f"Error in ACE++ image generation, falling back to standard: {str(e)}")
            logger.warning("Falling back to standard image generation without ACE++...")
            return await self._generate_images_without_ace(
                cover_image_prompt, scene_image_prompts, is_free,
                extra_negative_prompt=extra_negative_prompt,
                cover_negative_prompt=cover_negative_prompt,
            )

    async def _generate_images_without_ace(
        self,
        cover_image_prompt: str,
        scene_image_prompts: List[str],
        is_free: bool,
        extra_negative_prompt: Optional[str] = None,
        cover_negative_prompt: Optional[str] = None,
        cache_dir: Optional[str] = None,
    ) -> List[SceneImage]:
        """
        Image generation without ACE++.
        Initial round uses a single batched API request (1 auth + N inference tasks)
        for maximum throughput. Failed images are retried individually with backoff.
        cover_negative_prompt overrides extra_negative_prompt for index 0 (the cover).
        """
        RETRY_ROUNDS = 2       # Extra rounds to retry failed images
        BACKOFF_SECONDS = 3    # Pause before each retry round

        try:
            all_prompts = [cover_image_prompt] + scene_image_prompts
            total = len(all_prompts)

            # Build initial task list — 4-tuple includes per-image negative prompt
            # Cover (index 0) uses cover_negative_prompt; scenes use extra_negative_prompt
            pending = []
            for i, prompt in enumerate(all_prompts):
                scene_id = f"scene_{i+1}"
                neg = cover_negative_prompt if i == 0 else extra_negative_prompt
                pending.append((i, scene_id, prompt, neg))

            # results[i] will hold the final SceneImage for position i
            results: List[Optional[SceneImage]] = [None] * total

            # ── Round 0: Batched API request ──
            import uuid as _uuid
            logger.info(f"Generating {len(pending)} images (initial batch)...")
            t0_batch = time.perf_counter()

            # Build batch prompt list with unique task UUIDs
            batch_prompts = []
            uuid_to_pending = {}  # taskUUID → (idx, scene_id, prompt, neg)
            for idx, sid, prompt, neg in pending:
                task_uuid = str(_uuid.uuid4())
                batch_prompts.append({
                    "task_uuid": task_uuid,
                    "positive_prompt": prompt,
                    "negative_prompt": neg,
                })
                uuid_to_pending[task_uuid] = (idx, sid, prompt, neg)

            batch_failed = False
            try:
                url_map = await ai_config.generate_images_batch(
                    batch_prompts, seed=self._book_seed
                )
            except Exception as e:
                logger.warning(f"Batch API call failed, falling back to individual requests: {e}")
                url_map = {}
                batch_failed = True

            # Validate returned images concurrently, caching to disk if cache_dir provided
            if url_map:
                async def _validate_and_store(task_uuid: str, image_url: str):
                    idx, sid, prompt, neg = uuid_to_pending[task_uuid]
                    result = await self._validate_remote_image(image_url, cache_dir=cache_dir)
                    if result is False:
                        logger.warning(f"Image validation failed for {sid} in batch")
                        return False
                    cached_path = result if isinstance(result, str) else None
                    results[idx] = SceneImage(
                        scene_id=sid,
                        image_url=image_url,
                        prompt=prompt,
                        created_at=self._get_current_timestamp(),
                        cached_path=cached_path,
                    )
                    return True

                validation_tasks = [
                    _validate_and_store(tuuid, url)
                    for tuuid, url in url_map.items()
                ]
                await asyncio.gather(*validation_tasks)

            batch_elapsed = time.perf_counter() - t0_batch
            succeeded = sum(1 for r in results if r is not None)
            logger.info(
                f"Batch round completed in {batch_elapsed:.2f}s: "
                f"{succeeded}/{total} images succeeded"
            )

            # Collect still-failed for retry rounds
            still_failed = [
                (idx, sid, prompt, neg) for idx, sid, prompt, neg in pending
                if results[idx] is None
            ]

            if not still_failed:
                logger.info(f"All {total} images generated successfully (initial batch).")
                return [r for r in results if r is not None]

            # ── Batch-failure fast-path: fire all failed images concurrently, no sleep ──
            # When the entire batch call raised an exception (e.g. a safety block on one
            # prompt poisons the whole request), retry ALL images concurrently right away
            # rather than entering the backoff retry rounds — avoids the cumulative sleep penalty.
            if batch_failed:
                logger.warning(
                    f"Batch call failed — firing {len(still_failed)} individual requests concurrently..."
                )
                fallback_tasks = [
                    self._generate_single_image_with_seed(
                        sid, prompt, is_free, extra_negative_prompt=neg
                    )
                    for _, sid, prompt, neg in still_failed
                ]
                fallback_results = await asyncio.gather(*fallback_tasks, return_exceptions=True)
                new_still_failed = []
                for (idx, sid, prompt, neg), result in zip(still_failed, fallback_results):
                    if isinstance(result, BaseException):
                        logger.warning(f"Image {sid} failed in batch-fallback: {result}")
                        new_still_failed.append((idx, sid, prompt, neg))
                    else:
                        results[idx] = result
                still_failed = new_still_failed
                if not still_failed:
                    logger.info(f"All {total} images generated successfully (batch-fallback).")
                    return [r for r in results if r is not None]

            # ── Rounds 1+: Individual retries for failed images ──
            pending = still_failed
            for round_num in range(1, 1 + RETRY_ROUNDS):
                logger.warning(
                    f"Retry round {round_num}/{RETRY_ROUNDS}: "
                    f"retrying {len(pending)} failed image(s) after {BACKOFF_SECONDS}s backoff..."
                )
                await asyncio.sleep(BACKOFF_SECONDS)

                label = f"retry {round_num}"
                logger.info(f"Generating {len(pending)} images ({label})...")

                # Fire failed images concurrently via individual calls
                tasks = [
                    self._generate_single_image_with_seed(
                        sid, prompt, is_free, extra_negative_prompt=neg
                    )
                    for _, sid, prompt, neg in pending
                ]
                batch_results = await asyncio.gather(*tasks, return_exceptions=True)

                still_failed = []
                for (idx, sid, prompt, neg), result in zip(pending, batch_results):
                    if isinstance(result, BaseException):
                        logger.warning(f"Image {sid} failed ({label}): {result}")
                        still_failed.append((idx, sid, prompt, neg))
                    else:
                        results[idx] = result

                if not still_failed:
                    logger.info(f"All {total} images generated successfully ({label}).")
                    return [r for r in results if r is not None]

                pending = still_failed

            # All retry rounds exhausted — raise so the task reports failure
            failed_ids = [sid for _, sid, _, _ in pending]
            raise Exception(
                f"Image generation failed for {len(failed_ids)} image(s) after "
                f"{RETRY_ROUNDS} retry rounds: {', '.join(failed_ids)}"
            )

        except Exception as e:
            logger.error(f"Error generating scene images: {str(e)}")
            raise e

    async def _validate_remote_image(self, url: str, cache_dir: str | None = None) -> bool | str:
        """
        Download an image URL into memory and validate it with PIL.

        This is a lightweight check that catches corrupt/truncated images
        BEFORE they are stored in a SceneImage, allowing the caller to
        regenerate via a fresh Runware API call.

        Args:
            url: Remote image URL to validate.
            cache_dir: If provided, save the validated image to this directory
                       and return the local file path instead of True.

        Returns:
            - False if validation failed.
            - True if valid and no cache_dir.
            - Local file path (str) if valid and cached successfully.
        """
        import httpx
        from PIL import Image
        
        last_error = None
        for attempt in range(3):
            try:
                if attempt > 0:
                    delay = 0.5 * (2 ** (attempt - 1))
                    await asyncio.sleep(delay)
                
                async with httpx.AsyncClient(timeout=20.0) as client:
                    resp = await client.get(url)
                    resp.raise_for_status()
                
                img = Image.open(io.BytesIO(resp.content))
                img.verify()

                if cache_dir:
                    import os
                    from urllib.parse import urlparse
                    filename = os.path.basename(urlparse(url).path) or f"img_{hash(url)}.jpg"
                    local_path = os.path.join(cache_dir, filename)
                    with open(local_path, "wb") as f:
                        f.write(resp.content)
                    return local_path

                return True
            except Exception as e:
                last_error = e
                logger.warning(f"Remote image validation attempt {attempt + 1} failed for {url[:80]}: {e}")
                
        logger.error(f"Remote image validation completely failed after 3 attempts: {last_error}")
        return False

    async def _generate_single_image_with_seed(
        self, scene_id: str, prompt: str, is_free: bool, extra_negative_prompt: Optional[str] = None
    ) -> SceneImage:
        """
        Generate an image for a single scene (original method without ACE++).

        Validates every generated image with PIL to catch corrupt/truncated
        responses from Runware.  If validation fails, requests a *fresh*
        generation (with a bumped seed) — re-downloading the same URL would
        return the identical corrupt file.
        """
        MAX_ATTEMPTS = settings.IMAGE_GENERATION_VALIDATION_MAX_ATTEMPTS
        last_error: Optional[Exception] = None
        current_seed = self._book_seed

        for attempt in range(1, MAX_ATTEMPTS + 1):
            try:
                t0 = time.perf_counter()
                # Generate the image using standard generation
                image_url = await ai_config.generate_image(
                    prompt, is_free, seed=current_seed, extra_negative_prompt=extra_negative_prompt
                )

                # Validate the image is not corrupt before storing
                if await self._validate_remote_image(image_url):
                    scene_image = SceneImage(
                        scene_id=scene_id,
                        image_url=image_url,
                        prompt=prompt,
                        created_at=self._get_current_timestamp(),
                        seed=current_seed,
                    )
                    if attempt > 1:
                        logger.info(
                            f"Generated image for scene {scene_id} in {time.perf_counter() - t0:.2f}s "
                            f"(succeeded on attempt {attempt}/{MAX_ATTEMPTS})"
                        )
                    else:
                        logger.info(f"Generated image for scene {scene_id} in {time.perf_counter() - t0:.2f}s")
                    return scene_image

                # Validation failed — log and retry with a different seed
                logger.warning(
                    f"Image validation failed for scene {scene_id} "
                    f"(attempt {attempt}/{MAX_ATTEMPTS}), "
                    f"requesting fresh generation from Runware..."
                )
                if current_seed is not None:
                    current_seed += 1

            except RunwareSafetyBlockError:
                # The prompt triggered Runware's content filter.
                # Apply sanitisation (boy/girl/child -> character) on the first block,
                # but if it fails on attempt 2+, immediately return a placeholder to avoid pipeline delay.
                if attempt > 1:
                    logger.error(
                        f"Safety block persisted for scene {scene_id} on attempt {attempt}. "
                        f"Returning placeholder immediately to prevent retry delays."
                    )
                    placeholder_url = self._create_placeholder_image(scene_id)
                    return SceneImage(
                        scene_id=scene_id,
                        image_url=placeholder_url,
                        prompt=prompt,
                        created_at=self._get_current_timestamp(),
                    )

                import re
                prompt = re.sub(
                    r'\b(?:boy|girl|child|children|kid|kids|toddler|baby|infant|teen|teenager)\b',
                    'character',
                    prompt,
                    flags=re.IGNORECASE,
                )
                logger.warning(
                    f"Safety block for scene {scene_id} "
                    f"(attempt {attempt}/{MAX_ATTEMPTS}), "
                    f"retrying with sanitised prompt..."
                )
                if current_seed is not None:
                    current_seed += 1
                continue

            except Exception as e:
                logger.error(
                    f"Error generating image for scene {scene_id} "
                    f"(attempt {attempt}/{MAX_ATTEMPTS}): {str(e)}"
                )
                if attempt < MAX_ATTEMPTS:
                    if current_seed is not None:
                        current_seed += 1
                    continue
                # On the final attempt, do not raise the exception; let it fall through
                # to the placeholder creation below so the generation can finish.
                logger.warning(f"Exhausted all attempts for scene {scene_id}. Proceeding with placeholder.")

        # All validation attempts exhausted — generate a placeholder so the book
        # still gets created rather than failing entirely.
        logger.error(
            f"All {MAX_ATTEMPTS} image generation attempts returned corrupt images "
            f"for scene {scene_id}. Using placeholder image as fallback."
        )
        placeholder_url = self._create_placeholder_image(scene_id)
        return SceneImage(
            scene_id=scene_id,
            image_url=placeholder_url,
            prompt=prompt,
            created_at=self._get_current_timestamp(),
        )

    @staticmethod
    def _create_placeholder_image(scene_id: str) -> str:
        """
        Generate a soft placeholder image when Runware is unavailable.

        Creates a gentle pastel gradient (768×1024, matching Runware output
        dimensions) that works cleanly through the entire PDF pipeline —
        PIL, cv2, text overlay, watermarking all handle it correctly.

        Returns:
            str: file:// URL to the placeholder JPEG in /tmp.
        """
        from PIL import Image, ImageDraw
        import tempfile
        import os

        width, height = 768, 1024
        # Soft pastel gradient — visually gentle, won't clash with text overlay
        img = Image.new("RGB", (width, height), (230, 235, 245))
        draw = ImageDraw.Draw(img)

        # Add a subtle vertical gradient for visual interest
        for y in range(height):
            r = int(230 - (y / height) * 20)  # 230 → 210
            g = int(235 - (y / height) * 15)  # 235 → 220
            b = int(245 - (y / height) * 10)  # 245 → 235
            draw.line([(0, y), (width, y)], fill=(r, g, b))

        # Save to /tmp — the PDF pipeline temp cleanup will handle removal
        placeholder_path = os.path.join(
            tempfile.gettempdir(), f"placeholder_{scene_id}.jpg"
        )
        img.save(placeholder_path, "JPEG", quality=90)
        logger.info(f"Created placeholder image for scene {scene_id}: {placeholder_path}")
        return f"file://{placeholder_path}"

    def _get_current_timestamp(self) -> str:
        """
        Get the current timestamp in ISO format.
        """
        from datetime import datetime

        return str(datetime.now().isoformat())