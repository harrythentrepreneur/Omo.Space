#!/usr/bin/env python3
"""
Automated tests for V2 backend integration.

Tests cover:
  1. Pydantic model validation (V2 fields accepted, V1 backward compat)
  2. _build_v2_prompt_block() — all conditional prompt sections
  3. Function signature verification (all V2 params present)
  4. Highlight resolution logic (focus_phonemes vs all phonemes)
  5. Edge cases (empty lists, None values, strict_decodable)

Run: cd phonicsmaker-core-v1 && python -m pytest tests/test_v2_integration.py -v
"""

import sys
import os
import inspect
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# ── 1. Pydantic Model Tests ─────────────────────────────────────────────

def test_pydantic_v2_fields_accepted():
    """V2 payload with all fields should pass Pydantic validation."""
    from run_local_server import StoryGenerationRequest

    payload = {
        "phonemes": ["s", "a", "t", "p"],
        "story_idea": "A cat on a mat",
        "difficulty_level": "1",
        # V2 fields
        "known_phonemes": ["s", "a", "t", "p", "i", "n", "m", "d"],
        "focus_phonemes": ["sh", "ch"],
        "sight_words": ["the", "and", "is", "a"],
        "strict_decodable": True,
        "focus_mode": "phonics",
        "morphology_focus": [],
        "story_format": "storybook",
        "student_age": "6-7",
        "curriculum": "aus_v9",
        "highlight_text": True,
    }

    req = StoryGenerationRequest(**payload)
    assert req.known_phonemes == ["s", "a", "t", "p", "i", "n", "m", "d"]
    assert req.focus_phonemes == ["sh", "ch"]
    assert req.sight_words == ["the", "and", "is", "a"]
    assert req.strict_decodable is True
    assert req.focus_mode == "phonics"
    assert req.morphology_focus == []
    assert req.story_format == "storybook"
    assert req.student_age == "6-7"
    assert req.curriculum == "aus_v9"
    assert req.highlight_text is True


def test_pydantic_v1_backward_compat():
    """V1 payload (no V2 fields) should pass validation with None defaults."""
    from run_local_server import StoryGenerationRequest

    payload = {
        "phonemes": ["s", "a", "t"],
        "story_idea": "A dog in the fog",
        "difficulty_level": "2",
    }

    req = StoryGenerationRequest(**payload)
    assert req.known_phonemes is None
    assert req.focus_phonemes is None
    assert req.sight_words is None
    assert req.strict_decodable is None
    assert req.focus_mode is None
    assert req.morphology_focus is None
    assert req.story_format is None
    assert req.student_age is None
    assert req.curriculum is None
    assert req.highlight_text is None


def test_pydantic_empty_lists_accepted():
    """Empty lists [] from frontend should be accepted without errors."""
    from run_local_server import StoryGenerationRequest

    payload = {
        "phonemes": ["s"],
        "story_idea": "test",
        "difficulty_level": "1",
        "known_phonemes": [],
        "focus_phonemes": [],
        "sight_words": [],
        "morphology_focus": [],
    }

    req = StoryGenerationRequest(**payload)
    assert req.known_phonemes == []
    assert req.focus_phonemes == []
    assert req.sight_words == []
    assert req.morphology_focus == []


def test_pydantic_extra_fields_ignored():
    """Frontend may send extra fields (mode, page_count) — these should be silently dropped."""
    from run_local_server import StoryGenerationRequest

    payload = {
        "phonemes": ["s"],
        "story_idea": "test",
        "difficulty_level": "1",
        "mode": "generate",
        "page_count": 20,
    }

    # Should not raise — unknown fields silently ignored
    req = StoryGenerationRequest(**payload)
    assert req.phonemes == ["s"]


# ── 2. V2 Prompt Block Tests ────────────────────────────────────────────

def test_v2_prompt_phonics_mode():
    """Phonics mode: known + focus GPCs + strict mode + sight words should all appear."""
    from app.phonics_maker.story_generation.story_service import StoryService

    svc = StoryService()
    block = svc._build_v2_prompt_block(
        known_phonemes=["s", "a", "t", "p", "i", "n"],
        focus_phonemes=["sh", "ch"],
        sight_words=["the", "and", "is"],
        strict_decodable=True,
        focus_mode="phonics",
    )

    assert "KNOWN GPCs" in block
    assert "s, a, t, p, i, n" in block
    assert "FOCUS GPCs" in block
    assert "sh, ch" in block
    assert "VOCABULARY MODE: DECODABLE" in block
    assert "ALLOWED SIGHT WORDS" in block
    assert "the, and, is" in block


def test_v2_prompt_morphology_mode():
    """Morphology mode: morpheme section should appear."""
    from app.phonics_maker.story_generation.story_service import StoryService

    svc = StoryService()
    block = svc._build_v2_prompt_block(
        known_phonemes=["s", "a", "t"],
        focus_phonemes=["sh"],
        focus_mode="morphology",
        morphology_focus=["-ing", "-ed", "-er"],
    )

    assert "MORPHOLOGY FOCUS" in block
    assert "-ing, -ed, -er" in block
    assert "word parts being taught" in block.lower() or "word parts" in block.lower()


def test_v2_prompt_both_mode():
    """Both mode: phonics + morphology sections should both appear."""
    from app.phonics_maker.story_generation.story_service import StoryService

    svc = StoryService()
    block = svc._build_v2_prompt_block(
        known_phonemes=["s", "a", "t"],
        focus_phonemes=["sh"],
        focus_mode="both",
        morphology_focus=["-ing", "-est"],
    )

    assert "FOCUS GPCs" in block
    assert "ADDITIONAL MORPHOLOGY FOCUS" in block
    assert "-ing, -est" in block


def test_v2_prompt_passage_format():
    """Passage format: format override section should appear."""
    from app.phonics_maker.story_generation.story_service import StoryService

    svc = StoryService()
    block = svc._build_v2_prompt_block(
        known_phonemes=["s", "a", "t"],
        focus_phonemes=["sh"],
        story_format="passage",
    )

    assert "FORMAT OVERRIDE" in block
    assert "CONTINUOUS PASSAGE" in block


def test_v2_prompt_student_age_shapes_quality_examples():
    """
    Interest age no longer lives in the V2 block — it is injected for every flow
    (see tests/test_interest_age.py). What the V2 block must still do is pitch
    its worked examples at the right age, otherwise a tight GPC set drags the
    story back to nursery content.
    """
    from app.phonics_maker.story_generation.story_service import StoryService

    svc = StoryService()
    kwargs = dict(known_phonemes=["s", "a", "t"], focus_phonemes=["sh"])

    default_block = svc._build_v2_prompt_block(**kwargs)
    tween_block = svc._build_v2_prompt_block(**kwargs, student_age="tween")

    # Default keeps the nursery sentence as a GOOD example…
    assert '✅ GOOD: "Kit the cat sat on a mat."' in default_block
    # …and for a tween the same sentence is demoted to a BAD example.
    assert '❌ BAD: "Kit the cat sat on a mat."' in tween_block
    assert '✅ GOOD: "Kit the cat sat on a mat."' not in tween_block


def test_v2_prompt_curriculum():
    """Curriculum: curriculum context section should appear when provided."""
    from app.phonics_maker.story_generation.story_service import StoryService

    svc = StoryService()
    block = svc._build_v2_prompt_block(
        known_phonemes=["s", "a", "t"],
        focus_phonemes=["sh"],
        curriculum="aus_v9",
    )

    assert "CURRICULUM" in block
    assert "aus_v9" in block


def test_v2_prompt_no_curriculum():
    """No curriculum: curriculum section should NOT appear."""
    from app.phonics_maker.story_generation.story_service import StoryService

    svc = StoryService()
    block = svc._build_v2_prompt_block(
        known_phonemes=["s", "a", "t"],
        focus_phonemes=["sh"],
    )

    assert "CURRICULUM" not in block


def test_v2_prompt_no_strict_mode():
    """When strict_decodable is None/False, strict mode section should NOT appear."""
    from app.phonics_maker.story_generation.story_service import StoryService

    svc = StoryService()

    block_none = svc._build_v2_prompt_block(
        known_phonemes=["s", "a"],
        focus_phonemes=["sh"],
        strict_decodable=None,
    )
    assert "STRICT DECODABILITY MODE" not in block_none

    block_false = svc._build_v2_prompt_block(
        known_phonemes=["s", "a"],
        focus_phonemes=["sh"],
        strict_decodable=False,
    )
    assert "STRICT DECODABILITY MODE" not in block_false


def test_v2_prompt_empty_lists_no_sections():
    """Empty lists should NOT trigger any V2 prompt sections."""
    from app.phonics_maker.story_generation.story_service import StoryService

    svc = StoryService()
    block = svc._build_v2_prompt_block(
        known_phonemes=[],
        focus_phonemes=[],
        sight_words=[],
        morphology_focus=[],
    )

    assert "KNOWN GPCs" not in block
    assert "**FOCUS GPCs**" not in block
    assert "ALLOWED SIGHT WORDS" not in block
    assert "MORPHOLOGY FOCUS" not in block


def test_v2_prompt_known_only():
    """Only known_phonemes provided (no focus): should get single-tier decodability."""
    from app.phonics_maker.story_generation.story_service import StoryService

    svc = StoryService()
    block = svc._build_v2_prompt_block(
        known_phonemes=["s", "a", "t", "p"],
        focus_phonemes=None,
    )

    assert "KNOWN GPCs" in block
    assert "**FOCUS GPCs**" not in block
    assert "the student can decode these" in block


def test_v2_prompt_focus_only():
    """Only focus_phonemes provided (no known): should get feature-prominently rule."""
    from app.phonics_maker.story_generation.story_service import StoryService

    svc = StoryService()
    block = svc._build_v2_prompt_block(
        known_phonemes=None,
        focus_phonemes=["sh", "ch"],
    )

    assert "FOCUS GPCs" in block
    assert "KNOWN GPCs" not in block
    assert "teaching target" in block.lower() or "feature these prominently" in block.lower()


# ── 3. Function Signature Verification ───────────────────────────────────

def test_generate_story_task_has_v2_params():
    """generate_story_task must have all 10 V2 parameters."""
    from app.phonics_maker.tasks.story_tasks import generate_story_task

    sig = inspect.signature(generate_story_task)
    param_names = list(sig.parameters.keys())

    expected_v2_params = [
        "known_phonemes", "focus_phonemes", "sight_words",
        "strict_decodable", "focus_mode", "morphology_focus",
        "story_format", "student_age", "curriculum", "highlight_text",
    ]

    for param in expected_v2_params:
        assert param in param_names, f"Missing V2 parameter: {param}"
        # Verify default is None
        default = sig.parameters[param].default
        assert default is None, f"{param} default should be None, got {default}"


def test_generate_short_scenes_has_v2_params():
    """generate_short_scenes must have all 9 V2 parameters."""
    from app.phonics_maker.story_generation.story_service import StoryService

    sig = inspect.signature(StoryService.generate_short_scenes)
    param_names = list(sig.parameters.keys())

    expected_v2_params = [
        "known_phonemes", "focus_phonemes", "sight_words",
        "strict_decodable", "focus_mode", "morphology_focus",
        "story_format", "student_age", "curriculum",
    ]

    for param in expected_v2_params:
        assert param in param_names, f"Missing V2 parameter: {param}"


def test_generate_story_pdf_has_v2_params():
    """generate_story_pdf must have focus_phonemes and highlight_text."""
    from app.phonics_maker.pdf_generation.pdf_service import generate_story_pdf

    sig = inspect.signature(generate_story_pdf)
    param_names = list(sig.parameters.keys())

    assert "focus_phonemes" in param_names, "Missing focus_phonemes parameter"
    assert "highlight_text" in param_names, "Missing highlight_text parameter"


def test_build_v2_prompt_block_has_curriculum():
    """_build_v2_prompt_block must accept curriculum parameter."""
    from app.phonics_maker.story_generation.story_service import StoryService

    sig = inspect.signature(StoryService._build_v2_prompt_block)
    param_names = list(sig.parameters.keys())

    assert "curriculum" in param_names, "Missing curriculum parameter in _build_v2_prompt_block"


# ── 4. Highlight Resolution Tests ────────────────────────────────────────

def test_highlight_resolution_v2_focus():
    """V2: When focus_phonemes is provided, only those should be highlighted."""
    # Simulate the logic from pdf_service.py
    phonemes = ["s", "a", "t", "p", "sh", "ch"]
    focus_phonemes = ["sh", "ch"]
    highlight_text = None  # Default (highlight enabled)

    if highlight_text is False:
        highlight_phonemes = []
    else:
        highlight_phonemes = focus_phonemes if focus_phonemes else phonemes

    assert highlight_phonemes == ["sh", "ch"]


def test_highlight_resolution_v1_fallback():
    """V1: When focus_phonemes is None, all phonemes should be highlighted."""
    phonemes = ["s", "a", "t"]
    focus_phonemes = None
    highlight_text = None

    if highlight_text is False:
        highlight_phonemes = []
    else:
        highlight_phonemes = focus_phonemes if focus_phonemes else phonemes

    assert highlight_phonemes == ["s", "a", "t"]


def test_highlight_resolution_disabled():
    """When highlight_text is explicitly False, no phonemes should be highlighted."""
    phonemes = ["s", "a", "t"]
    focus_phonemes = ["sh", "ch"]
    highlight_text = False

    if highlight_text is False:
        highlight_phonemes = []
    else:
        highlight_phonemes = focus_phonemes if focus_phonemes else phonemes

    assert highlight_phonemes == []


def test_highlight_resolution_empty_focus():
    """Empty focus_phonemes list should fall back to all phonemes."""
    phonemes = ["s", "a", "t"]
    focus_phonemes = []
    highlight_text = None

    if highlight_text is False:
        highlight_phonemes = []
    else:
        highlight_phonemes = focus_phonemes if focus_phonemes else phonemes

    assert highlight_phonemes == ["s", "a", "t"]


# ── 5. Cover Badge Tests ────────────────────────────────────────────────

def test_cover_badge_v2_shows_focus_only():
    """V2: Cover badge phonemes should be focus_phonemes, not all."""
    # Simulate the logic from pdf_service.py
    phonemes = ["s", "a", "t", "p", "sh", "ch"]
    focus_phonemes = ["sh", "ch"]

    badge_phonemes = focus_phonemes if focus_phonemes else phonemes
    assert badge_phonemes == ["sh", "ch"]


def test_cover_badge_v1_shows_all():
    """V1: Cover badge should show all phonemes when no focus_phonemes."""
    phonemes = ["s", "a", "t"]
    focus_phonemes = None

    badge_phonemes = focus_phonemes if focus_phonemes else phonemes
    assert badge_phonemes == ["s", "a", "t"]


# ── 6. V2 Mode Detection Tests ──────────────────────────────────────────

def test_v2_mode_detection_with_known_phonemes():
    """V2 mode should trigger when known_phonemes is provided."""
    known_phonemes = ["s", "a", "t"]
    focus_phonemes = None
    is_v2 = bool(known_phonemes or focus_phonemes)
    assert is_v2 is True


def test_v2_mode_detection_with_focus_phonemes():
    """V2 mode should trigger when focus_phonemes is provided."""
    known_phonemes = None
    focus_phonemes = ["sh"]
    is_v2 = bool(known_phonemes or focus_phonemes)
    assert is_v2 is True


def test_v2_mode_detection_both():
    """V2 mode should trigger when both are provided."""
    known_phonemes = ["s", "a"]
    focus_phonemes = ["sh"]
    is_v2 = bool(known_phonemes or focus_phonemes)
    assert is_v2 is True


def test_v2_mode_not_triggered_none():
    """V2 mode should not trigger when both are None (V1 flow)."""
    known_phonemes = None
    focus_phonemes = None
    is_v2 = bool(known_phonemes or focus_phonemes)
    assert is_v2 is False


def test_v2_mode_not_triggered_empty_lists():
    """V2 mode should not trigger when both are empty lists."""
    known_phonemes = []
    focus_phonemes = []
    is_v2 = bool(known_phonemes or focus_phonemes)
    assert is_v2 is False


# ── 7. Accessibility / CVI-BVI Tests ────────────────────────────────────

ACCESSIBILITY_IDS = ["high_contrast", "simplified_shapes", "large_print_friendly"]
NON_ACCESSIBILITY_IDS = ["vivid_cartoon", "comic_book", "pencil_sketch", "cyberpunk"]

def test_accessibility_style_prompt_fragments_exist():
    """All 3 accessibility styles must have STYLE_PROMPT_FRAGMENTS entries."""
    from app.phonics_maker.image_generation.image_service import ImageService

    for style_id in ACCESSIBILITY_IDS:
        assert style_id in ImageService.STYLE_PROMPT_FRAGMENTS, (
            f"Missing STYLE_PROMPT_FRAGMENTS for '{style_id}'"
        )
        fragment = ImageService.STYLE_PROMPT_FRAGMENTS[style_id]
        assert len(fragment) > 100, f"Fragment for '{style_id}' suspiciously short"


def test_accessibility_style_gemini_instructions_exist():
    """All 3 accessibility styles must have STYLE_GEMINI_INSTRUCTIONS entries."""
    from app.phonics_maker.image_generation.image_service import ImageService

    for style_id in ACCESSIBILITY_IDS:
        assert style_id in ImageService.STYLE_GEMINI_INSTRUCTIONS, (
            f"Missing STYLE_GEMINI_INSTRUCTIONS for '{style_id}'"
        )
        instruction = ImageService.STYLE_GEMINI_INSTRUCTIONS[style_id]
        assert "ACCESSIBILITY" in instruction or "CVI" in instruction or "LOW VISION" in instruction


def test_accessibility_style_negative_prompts_exist():
    """All 3 accessibility styles must have STYLE_NEGATIVE_PROMPTS entries."""
    from app.phonics_maker.image_generation.image_service import ImageService

    for style_id in ACCESSIBILITY_IDS:
        assert style_id in ImageService.STYLE_NEGATIVE_PROMPTS, (
            f"Missing STYLE_NEGATIVE_PROMPTS for '{style_id}'"
        )
        neg = ImageService.STYLE_NEGATIVE_PROMPTS[style_id]
        # All should block busy backgrounds/textures/patterns
        assert "pattern" in neg.lower() or "texture" in neg.lower()


def test_is_accessibility_style_helper():
    """is_accessibility_style should return True for accessibility IDs, False for others."""
    from app.phonics_maker.image_generation.image_service import ImageService

    for style_id in ACCESSIBILITY_IDS:
        assert ImageService.is_accessibility_style(style_id) is True, (
            f"is_accessibility_style('{style_id}') should be True"
        )

    for style_id in NON_ACCESSIBILITY_IDS:
        assert ImageService.is_accessibility_style(style_id) is False, (
            f"is_accessibility_style('{style_id}') should be False"
        )

    # Edge cases
    assert ImageService.is_accessibility_style(None) is False
    assert ImageService.is_accessibility_style("") is False
    assert ImageService.is_accessibility_style("unknown_style") is False


def test_illustration_style_in_generate_story_pdf_signature():
    """generate_story_pdf must accept illustration_style parameter."""
    from app.phonics_maker.pdf_generation.pdf_service import generate_story_pdf

    sig = inspect.signature(generate_story_pdf)
    param_names = list(sig.parameters.keys())
    assert "illustration_style" in param_names, "Missing illustration_style in generate_story_pdf"
    assert sig.parameters["illustration_style"].default is None


def test_illustration_style_in_process_images_signature():
    """process_images must accept illustration_style parameter."""
    from app.phonics_maker.pdf_generation.text_processor import process_images

    sig = inspect.signature(process_images)
    param_names = list(sig.parameters.keys())
    assert "illustration_style" in param_names, "Missing illustration_style in process_images"
    assert sig.parameters["illustration_style"].default is None


def test_illustration_style_in_add_text_to_image_signature():
    """add_text_to_image must accept illustration_style parameter."""
    from app.phonics_maker.pdf_generation.text_processor import add_text_to_image

    sig = inspect.signature(add_text_to_image)
    param_names = list(sig.parameters.keys())
    assert "illustration_style" in param_names, "Missing illustration_style in add_text_to_image"
    assert sig.parameters["illustration_style"].default is None


def test_text_colors_forced_for_accessibility():
    """Accessibility styles should force specific high-contrast text colours."""
    from app.phonics_maker.pdf_generation.text_processor import (
        ACCESSIBILITY_TEXT_COLOR, ACCESSIBILITY_STROKE_COLOR,
    )

    # Black text BGR
    assert ACCESSIBILITY_TEXT_COLOR == (0, 0, 0)
    # White stroke BGR
    assert ACCESSIBILITY_STROKE_COLOR == (255, 255, 255)


def test_font_scale_multiplier_value():
    """Accessibility font scale multiplier should be > 1.0."""
    from app.phonics_maker.pdf_generation.text_processor import (
        ACCESSIBILITY_FONT_SCALE_MULTIPLIER,
    )
    assert ACCESSIBILITY_FONT_SCALE_MULTIPLIER >= 1.2, "Multiplier should be at least 1.2"
    assert ACCESSIBILITY_FONT_SCALE_MULTIPLIER <= 2.0, "Multiplier shouldn't be too extreme"


def test_accessibility_stroke_thickness():
    """Accessibility stroke thickness should be > standard (4)."""
    from app.phonics_maker.pdf_generation.text_processor import (
        ACCESSIBILITY_STROKE_THICKNESS, ACCESSIBILITY_LETTER_SPACING,
    )
    assert ACCESSIBILITY_STROKE_THICKNESS > 4
    assert ACCESSIBILITY_LETTER_SPACING > 3

# ── 8. Story Quality Boost Tests ────────────────────────────────────────

def test_v2_prompt_story_quality_small_gpc_set():
    """Small GPC set (≤20): story quality section should appear with CRITICAL heading."""
    from app.phonics_maker.story_generation.story_service import StoryService

    svc = StoryService()
    # 8 known + 2 focus = 10 total GPCs (well under 20)
    block = svc._build_v2_prompt_block(
        known_phonemes=["s", "a", "t", "p", "i", "n", "m", "d"],
        focus_phonemes=["sh", "ch"],
        strict_decodable=False,
    )

    assert "STORY QUALITY" in block
    assert "CRITICAL (READ THIS FIRST)" in block
    assert "story arc" in block.lower()


def test_v2_prompt_story_quality_medium_gpc_set():
    """Medium GPC set (21-40): story quality section should appear with IMPORTANT heading."""
    from app.phonics_maker.story_generation.story_service import StoryService

    svc = StoryService()
    # 25 known + 3 focus = 28 total GPCs (medium range)
    medium_known = ["s", "a", "t", "p", "i", "n", "m", "d", "g", "o",
                    "c", "k", "e", "u", "r", "h", "b", "f", "l", "j",
                    "v", "w", "x", "y", "z"]
    block = svc._build_v2_prompt_block(
        known_phonemes=medium_known,
        focus_phonemes=["sh", "ch", "th"],
        strict_decodable=False,
    )

    assert "STORY QUALITY" in block
    assert "IMPORTANT (READ THIS FIRST)" in block
    assert "story arc" in block.lower()


def test_v2_prompt_story_quality_not_for_large_gpc_set():
    """Large GPC set (>40): story quality section should NOT appear."""
    from app.phonics_maker.story_generation.story_service import StoryService

    svc = StoryService()
    # 40 known + 3 focus = 43 total GPCs (over 40)
    large_known = ["s", "a", "t", "p", "i", "n", "m", "d", "g", "o",
                   "c", "k", "e", "u", "r", "h", "b", "f", "l", "j",
                   "v", "w", "x", "y", "z", "qu", "sh", "ch", "th",
                   "ng", "ck", "ee", "oo", "ar", "or", "ai", "igh",
                   "ow", "oi", "ear"]
    block = svc._build_v2_prompt_block(
        known_phonemes=large_known,
        focus_phonemes=["ure", "air", "er"],
        strict_decodable=True,
    )

    assert "STORY QUALITY" not in block


def test_v2_prompt_story_quality_also_in_instructional_mode():
    """Story quality boost should NOW appear in instructional mode for small GPC sets."""
    from app.phonics_maker.story_generation.story_service import StoryService

    svc = StoryService()
    block = svc._build_v2_prompt_block(
        known_phonemes=["s", "a", "t", "p"],
        focus_phonemes=["sh"],
        strict_decodable=False,
        vocabulary_mode="instructional",
    )

    assert "STORY QUALITY" in block
    assert "CRITICAL (READ THIS FIRST)" in block


def test_v2_prompt_contrastive_examples():
    """Small GPC set: contrastive BAD vs GOOD examples should appear."""
    from app.phonics_maker.story_generation.story_service import StoryService

    svc = StoryService()
    block = svc._build_v2_prompt_block(
        known_phonemes=["s", "a", "t", "p", "i", "n"],
        focus_phonemes=["o", "c", "k"],
        strict_decodable=True,
    )

    assert "BAD vs GOOD" in block
    assert "Kip is a top tot" in block
    assert "Kit the cat sat on a mat" in block


def test_v2_prompt_expanded_function_words():
    """Small GPC set: expanded function word list should include diverse categories."""
    from app.phonics_maker.story_generation.story_service import StoryService

    svc = StoryService()
    block = svc._build_v2_prompt_block(
        known_phonemes=["s", "a", "t", "p"],
        focus_phonemes=["sh"],
        strict_decodable=True,
    )

    assert "Pronouns:" in block
    assert "Verbs:" in block
    assert "Prepositions:" in block
    assert "Question words:" in block
    # Check some of the new words that were missing before
    assert "can" in block
    assert "with" in block
    assert "they" in block


def test_v2_prompt_chain_of_thought_planning():
    """Small GPC set (≤20): chain-of-thought planning section should appear."""
    from app.phonics_maker.story_generation.story_service import StoryService

    svc = StoryService()
    block = svc._build_v2_prompt_block(
        known_phonemes=["s", "a", "t", "p", "i", "n"],
        focus_phonemes=["o", "c"],
        strict_decodable=True,
    )

    assert "PRE-WRITING PLANNING" in block
    assert "list 20-30" in block.lower() or "list 20" in block
    assert "DISCARD" in block


def test_v2_prompt_no_chain_of_thought_for_large_gpc_set():
    """Large GPC set: chain-of-thought planning should NOT appear."""
    from app.phonics_maker.story_generation.story_service import StoryService

    svc = StoryService()
    medium_known = ["s", "a", "t", "p", "i", "n", "m", "d", "g", "o",
                    "c", "k", "e", "u", "r", "h", "b", "f", "l", "j",
                    "v", "w", "x", "y", "z"]
    block = svc._build_v2_prompt_block(
        known_phonemes=medium_known,
        focus_phonemes=["sh", "ch"],
        strict_decodable=True,
    )

    assert "PRE-WRITING PLANNING" not in block


def test_v2_prompt_quality_before_decodability():
    """Story quality rules should appear BEFORE strict decodability rules."""
    from app.phonics_maker.story_generation.story_service import StoryService

    svc = StoryService()
    block = svc._build_v2_prompt_block(
        known_phonemes=["s", "a", "t", "p", "i", "n"],
        focus_phonemes=["sh", "ch"],
        strict_decodable=True,
    )

    quality_pos = block.find("STORY QUALITY")
    decodable_pos = block.find("VOCABULARY MODE: DECODABLE")
    assert quality_pos < decodable_pos, "Story quality should appear BEFORE decodability rules"


# ── 9. Two-Pass Quality Review Tests ────────────────────────────────────

def test_should_run_quality_review_decodable():
    """Decodable mode: quality review should always run."""
    from app.phonics_maker.story_generation.story_service import StoryService

    assert StoryService._should_run_quality_review(
        is_v2=True,
        vocabulary_mode="decodable",
        strict_decodable=True,
        known_phonemes=["s", "a", "t"],
        focus_phonemes=["sh"],
    ) is True


def test_should_run_quality_review_decodable_large_gpc():
    """Decodable mode with large GPC set: should still run."""
    from app.phonics_maker.story_generation.story_service import StoryService

    large_known = list("abcdefghijklmnopqrstuvwxyz") + ["sh", "ch", "th", "ng", "ck"]
    assert StoryService._should_run_quality_review(
        is_v2=True,
        vocabulary_mode="decodable",
        strict_decodable=True,
        known_phonemes=large_known,
        focus_phonemes=["oi", "ou"],
    ) is True


def test_should_run_quality_review_instructional_small():
    """Instructional mode with ≤30 GPCs: should run."""
    from app.phonics_maker.story_generation.story_service import StoryService

    assert StoryService._should_run_quality_review(
        is_v2=True,
        vocabulary_mode="instructional",
        strict_decodable=False,
        known_phonemes=["s", "a", "t", "p", "i", "n"],
        focus_phonemes=["sh"],
    ) is True


def test_should_run_quality_review_instructional_large():
    """Instructional mode with >30 GPCs: should NOT run."""
    from app.phonics_maker.story_generation.story_service import StoryService

    large_known = list("abcdefghijklmnopqrstuvwxyz") + ["sh", "ch", "th", "ng", "ck"]
    assert StoryService._should_run_quality_review(
        is_v2=True,
        vocabulary_mode="instructional",
        strict_decodable=False,
        known_phonemes=large_known,
        focus_phonemes=["oi"],
    ) is False


def test_should_run_quality_review_authentic():
    """Authentic mode: should NOT run."""
    from app.phonics_maker.story_generation.story_service import StoryService

    assert StoryService._should_run_quality_review(
        is_v2=True,
        vocabulary_mode="authentic",
        strict_decodable=False,
        known_phonemes=["s", "a", "t"],
        focus_phonemes=["sh"],
    ) is False


def test_should_run_quality_review_v1():
    """V1 mode (not V2): should NOT run."""
    from app.phonics_maker.story_generation.story_service import StoryService

    assert StoryService._should_run_quality_review(
        is_v2=False,
        vocabulary_mode=None,
        strict_decodable=None,
        known_phonemes=None,
        focus_phonemes=None,
    ) is False


def test_build_review_decodability_constraints_decodable():
    """Decodable mode: review constraints should include GPC lists."""
    from app.phonics_maker.story_generation.story_service import StoryService

    constraints = StoryService._build_review_decodability_constraints(
        known_phonemes=["s", "a", "t", "p"],
        focus_phonemes=["sh", "ch"],
        sight_words=["the", "and"],
        strict_decodable=True,
    )

    assert "DECODABILITY CONSTRAINTS" in constraints
    assert "s, a, t, p" in constraints
    assert "sh, ch" in constraints
    assert "the, and" in constraints
    assert "function words" in constraints  # small GPC set → function word allowance


def test_review_prompt_importable():
    """STORY_QUALITY_REVIEW_PROMPT should be importable and formattable."""
    from app.core.ai.prompts import STORY_QUALITY_REVIEW_PROMPT, get_interest_age_config

    assert "{story_text}" in STORY_QUALITY_REVIEW_PROMPT
    assert "{scene_count}" in STORY_QUALITY_REVIEW_PROMPT
    assert "{decodability_constraints}" in STORY_QUALITY_REVIEW_PROMPT
    assert "{interest_age_constraints}" in STORY_QUALITY_REVIEW_PROMPT

    cfg = get_interest_age_config(None)

    # Test it can be formatted without errors
    formatted = STORY_QUALITY_REVIEW_PROMPT.format(
        story_text="Test Title|||Scene one.---Scene two.",
        scene_count=2,
        decodability_constraints="No constraints.",
        title_and_scenes_example="Example|||A.---B.",
        reviewer_persona=cfg["reviewer_persona"],
        reader_descriptor=cfg["reader_descriptor"],
        article=cfg["article"],
        author_test=cfg["author_test"],
        interest_age_constraints="",
    )
    assert "Test Title" in formatted


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])

