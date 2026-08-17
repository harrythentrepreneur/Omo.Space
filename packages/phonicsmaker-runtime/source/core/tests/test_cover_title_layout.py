from pathlib import Path

from app.phonics_maker.image_generation.image_service import ImageService


def test_structured_cover_prompt_embeds_title_and_focus_sounds():
    service = ImageService()

    prompt, negative_prompt = service.build_structured_cover_prompt(
        story_title="The Fun Trip to the Snow",
        phonemes=["ai", "ee"],
        visual_description="Two friends playing beside a snowy river",
    )

    assert 'titled "The Fun Trip to the Snow"' in prompt
    assert 'Focus Sounds: ai, ee' in prompt
    assert negative_prompt == service.COVER_NEGATIVE_PROMPT


def test_cover_template_does_not_add_a_title_panel():
    template_path = Path(__file__).parents[1] / "templates" / "cover_page_template.html"
    template = template_path.read_text()

    assert "cover-content" not in template
    assert "{{ story_title }}" not in template
    assert "{{ cover_items }}" not in template
