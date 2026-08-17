# phonics_maker/pdf_generation/__init__.py

from app.phonics_maker.pdf_generation.pdf_service import generate_story_pdf
from app.phonics_maker.pdf_generation.html_renderer import HTMLRenderer
from app.phonics_maker.pdf_generation.pdf_generator import generate_pdf_from_html_pages
from app.phonics_maker.pdf_generation.text_processor import (
    add_text_to_image,
    create_cover_image,
    get_font_scale_for_difficulty,
    process_images,
)
from app.phonics_maker.pdf_generation.file_utils import (
    make_filesystem_safe,
    ensure_directory_exists,
    get_task_temp_dir,
    cleanup_task_temp_dir,
)
from app.phonics_maker.pdf_generation.layout_utils import generate_default_layout_json

__all__ = [
    "generate_story_pdf",
    "HTMLRenderer",
    "generate_pdf_from_html_pages",
    "add_text_to_image",
    "create_cover_image",
    "get_font_scale_for_difficulty",
    "process_images",
    "make_filesystem_safe",
    "ensure_directory_exists",
    "get_task_temp_dir",
    "cleanup_task_temp_dir",
    "generate_default_layout_json",
]
