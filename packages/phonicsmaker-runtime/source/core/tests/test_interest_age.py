"""
Interest age is decoupled from reading level.

Reading level (level_configs, 1-5) controls decoding. Interest age controls
themes, character ages, titles, tone and illustration framing. The pairing that
has to work is a LOW reading level with a HIGH interest age — the hi-lo case for
older struggling readers.
"""

import string

import pytest

from app.core.ai import prompts as P
from app.core.ai.prompts import (
    DEFAULT_INTEREST_AGE_BAND,
    INTEREST_AGE_CONFIGS,
    build_interest_age_block,
    get_interest_age_config,
    level_configs,
    resolve_interest_age_band,
)
from app.phonics_maker.story_generation.story_service import StoryService

OLDER_BANDS = [b for b in INTEREST_AGE_CONFIGS if b != DEFAULT_INTEREST_AGE_BAND]


# ── Band resolution ──────────────────────────────────────────────────


@pytest.mark.parametrize(
    "value,expected",
    [
        # Unset must stay on the historical default.
        (None, "early_years"),
        ("", "early_years"),
        # Exact band keys.
        ("early_years", "early_years"),
        ("tween", "tween"),
        ("teen", "teen"),
        ("adult", "adult"),
        # Legacy value the web app sent before this change.
        ("adult_learner", "adult"),
        # Free-text aliases.
        ("middle school", "tween"),
        ("teenager", "teen"),
        ("young_adult", "teen"),
        ("kids", "early_years"),
        # Numeric ages, including the ranges the V2 tests already used.
        ("6-7", "early_years"),
        ("9-10", "middle_primary"),
        ("12", "tween"),
        ("age 15", "teen"),
        ("22", "adult"),
        # Ranges resolve on the OLDEST age, so 11-13 is not middle_primary.
        ("11-13", "tween"),
        # Unrecognised input degrades to the default rather than crashing.
        ("banana", "early_years"),
    ],
)
def test_resolve_interest_age_band(value, expected):
    assert resolve_interest_age_band(value) == expected


def test_every_band_defines_every_key():
    """A missing key would raise KeyError mid-generation, not at import."""
    expected = set(INTEREST_AGE_CONFIGS[DEFAULT_INTEREST_AGE_BAND])
    for band, cfg in INTEREST_AGE_CONFIGS.items():
        assert set(cfg) == expected, f"{band} key mismatch"


# ── The block itself ─────────────────────────────────────────────────


def test_default_band_adds_no_block():
    """Existing early-years users must see no prompt change at all."""
    assert build_interest_age_block(None) == ""
    assert build_interest_age_block("early_years") == ""
    assert build_interest_age_block("5") == ""


@pytest.mark.parametrize("band", OLDER_BANDS)
def test_older_bands_add_a_dignity_scoped_block(band):
    block = build_interest_age_block(band)
    cfg = INTEREST_AGE_CONFIGS[band]

    assert "INTEREST AGE" in block
    assert cfg["label"].upper() in block
    assert "DIGNITY RULE" in block
    # The block must state that it overrides the level's content framing…
    assert "DECODING ONLY" in block
    # …and override the too-young title examples from level_configs.
    assert "TITLE OVERRIDE" in block
    assert cfg["title_examples"] in block
    assert cfg["avoid_themes"] in block


def test_tween_block_bans_the_babyish_content_that_lost_the_client():
    block = build_interest_age_block("tween").lower()
    for banned in ["nursery", "toddler", "talking toys", "naptime", "sing-song"]:
        assert banned in block, banned


# ── Prompt assembly: every prompt formats for every band × level ─────


def _base_prompt_vars(band, level_key):
    cfg = get_interest_age_config(band)
    lt = level_configs[level_key]
    user_level = lt["user_level"]
    return {
        "user_level": user_level,
        "word_count_range": lt["word_count_range"],
        "title_spec": lt["title_spec"],
        "vocab_guardrail": lt["vocab_guardrail"],
        "tone_description": lt["tone_description"],
        "story_idea": "a kid fixes a bike",
        "phonemes": ["sh"],
        "scene_count": 20,
        "language_variant_name": "US English",
        "phonics_use": lt["phonics_use"].format(
            phonemes=["sh"], language_variant_name="US English"
        ),
        "language_mechanics": lt["language_mechanics"].format(
            language_variant_name="US English",
            language_variant_instructions=P.LANGUAGE_SPECIFIC_INSTRUCTIONS["US"],
        ),
        "author_persona": cfg["author_persona"],
        "book_framing": cfg["book_framing"],
        "reader_descriptor": cfg["reader_descriptor"],
        "reader_target": cfg["reader_target_template"].format(user_level=user_level),
        "vocab_target": cfg["vocab_target_template"].format(user_level=user_level),
        "author_test": cfg["author_test"],
        "action_vocabulary": cfg["action_vocabulary"],
        "article": cfg["article"],
    }


@pytest.mark.parametrize("band", list(INTEREST_AGE_CONFIGS))
@pytest.mark.parametrize("level_key", ["1", "2", "3", "4", "5"])
def test_base_prompt_formats_for_every_band_and_level(band, level_key):
    prompt = P.BASE_STORY_GENERATION_PROMPT.format(**_base_prompt_vars(band, level_key))
    assert "{" not in prompt.replace("{phonemes}", "")


@pytest.mark.parametrize("band", list(INTEREST_AGE_CONFIGS))
def test_image_prompts_format_for_every_band(band):
    cfg = get_interest_age_config(band)
    P.COVER_IMAGE_PROMPT_GENERATION_PROMPT.format(
        story_idea="x",
        short_scenes="1. a",
        illustration_style_instruction="s",
        image_audience=cfg["image_audience"],
        image_clothing=cfg["image_clothing"],
    )
    P.DETAILED_SCENE_GENERATION_PROMPT.format(
        story_idea="x",
        all_short_scenes="a",
        cover_page_prompt="c",
        scene_number=1,
        scene="s",
        illustration_style_instruction="s",
        image_audience=cfg["image_audience"],
        image_clothing=cfg["image_clothing"],
        build_descriptors=cfg["build_descriptors"],
    )
    P.DETAILED_SCENE_GENERATION_PROMPT_MINIMAL.format(
        story_idea="x",
        cover_page_prompt="c",
        scene_number=1,
        scene="s",
        illustration_style_instruction="s",
        image_audience=cfg["image_audience"],
        build_descriptors=cfg["build_descriptors"],
    )
    P.CHARACTER_REFERENCE_PROMPT.format(
        story_idea="x",
        cover_image_prompt="c",
        illustration_style_instruction="s",
        image_audience=cfg["image_audience"],
        image_clothing=cfg["image_clothing"],
        build_descriptors=cfg["build_descriptors"],
    )
    P.CHARACTER_DESCRIPTION_EXTRACTION_PROMPT.format(
        cover_image_prompt="c",
        story_scenes="1. a",
        build_descriptors=cfg["build_descriptors"],
        image_audience=cfg["image_audience"],
    )


def test_no_prompt_hardcodes_a_child_audience():
    """
    Regression guard for the actual bug: phrases like "young audience" baked into
    a prompt cannot be overridden by any interest-age setting.
    """
    banned = ["a young audience", "picture-book story for", "typical {user_level} child"]
    for name in [
        "BASE_STORY_GENERATION_PROMPT",
        "STORY_QUALITY_REVIEW_PROMPT",
        "COVER_IMAGE_PROMPT_GENERATION_PROMPT",
        "DETAILED_SCENE_GENERATION_PROMPT",
        "DETAILED_SCENE_GENERATION_PROMPT_MINIMAL",
    ]:
        text = getattr(P, name)
        for phrase in banned:
            assert phrase not in text, f"{name} still hardcodes {phrase!r}"


# ── The hi-lo pairing: low reading level + high interest age ─────────


def test_level_1_tween_keeps_decoding_low_and_content_old():
    """Angela's case: a 12-year-old decoding at Level 1."""
    prompt = P.BASE_STORY_GENERATION_PROMPT.format(**_base_prompt_vars("tween", "1"))
    prompt += "\n" + build_interest_age_block("tween")

    # Decoding stays at Level 1 — the level's own guardrails are intact.
    assert "3-8 words" in prompt
    assert "CVC/CVCC" in prompt
    # Content is pitched at 11-13, and the model is told which dial is which.
    assert "11-13" in prompt
    assert "hi-lo" in prompt
    assert "DECODING ONLY" in prompt
    # No nursery framing survives.
    assert "picture-book story for Prep readers" not in prompt
    assert "a typical Prep child" not in prompt


def test_quality_review_prompt_carries_the_band():
    """
    The review pass used to undo the interest age by "simplifying" the story
    back into nursery content.
    """
    cfg = get_interest_age_config("tween")
    review = P.STORY_QUALITY_REVIEW_PROMPT.format(
        story_text="T|||a",
        scene_count=1,
        decodability_constraints="x",
        title_and_scenes_example="y",
        reviewer_persona=cfg["reviewer_persona"],
        reader_descriptor=cfg["reader_descriptor"],
        article=cfg["article"],
        author_test=cfg["author_test"],
        interest_age_constraints=build_interest_age_block("tween"),
    )
    assert "NEVER MAKE THE STORY YOUNGER" in review
    assert "11-13" in review
    assert "children's book editor and quality reviewer" not in review


def test_differentiate_prompt_carries_the_band():
    lt = level_configs["2"]
    prompt = P.DIFFERENTIATE_STORY_PROMPT.format(
        original_story="T|||a---b",
        target_level_name=lt["user_level"],
        language_variant_name="US English",
        word_count_range=lt["word_count_range"],
        scene_count=2,
        vocab_guardrail=lt["vocab_guardrail"],
        language_mechanics="x",
        interest_age_block=build_interest_age_block("teen"),
    )
    assert "14-17" in prompt
    assert "Never shift the themes, character ages, or tone toward a younger audience" in prompt


# ── The V1 regression that motivated moving the block ───────────────


def test_interest_age_applies_without_v2_fields():
    """
    The old implementation injected interest age inside the V2 block, so every
    non-V2 flow (free book, landing creator, book sets) silently ignored it.
    """
    svc = StoryService()
    v1_block = svc._build_v2_prompt_block(student_age="tween")
    assert "INTEREST AGE" not in v1_block  # no longer its job
    # …but the standalone block is available to every flow.
    assert "INTEREST AGE" in build_interest_age_block("tween")


def test_interest_age_block_does_not_loosen_decodability():
    """Themes are the band's business; word choice stays with the GPC rules."""
    block = build_interest_age_block(
        "tween", scope_note="\n**SCOPE:** decodability constraints above still govern word choice."
    )
    assert "decodability constraints above still govern" in block
