# phonics_maker/pdf_generation/pdf_generator.py

from typing import List
from datetime import datetime
import asyncio
import logging
import multiprocessing
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
from app.core.config.logger import logger
from app.core.utils.retry import retry
from app.core.config.config import settings

# Suppress noisy WeasyPrint CSS warnings (height: 100vh, text-shadow, box-shadow, etc.)
logging.getLogger('weasyprint').setLevel(logging.ERROR)
logging.getLogger('weasyprint.css').setLevel(logging.ERROR)
logging.getLogger('weasyprint.css.validation').setLevel(logging.ERROR)

# Suppress noisy fonttools logs (font subsetting debug output during PDF generation)
logging.getLogger('fontTools').setLevel(logging.WARNING)
logging.getLogger('fontTools.subset').setLevel(logging.WARNING)
logging.getLogger('fontTools.ttLib').setLevel(logging.WARNING)

# Use 'spawn' so worker processes don't inherit asyncio state or open file descriptors.
_mp_ctx = multiprocessing.get_context('spawn')

# Print-friendly variant: downsampled/re-encoded images for faster printer spooling.
# Text is embedded as vector glyphs, so only illustration sharpness is affected.
PRINT_VARIANT_SUFFIX = "_print"
PRINT_JPEG_QUALITY = 60
PRINT_DPI = 96

_process_pool = None
_pool_lock = asyncio.Lock()


async def _get_process_pool():
    global _process_pool
    if _process_pool is None:
        async with _pool_lock:
            if _process_pool is None:
                # Limit max workers to 4 (matching cpu count settings)
                _process_pool = ProcessPoolExecutor(
                    max_workers=4,
                    mp_context=_mp_ctx
                )
    return _process_pool


def _weasyprint_render_worker(
    html_pages: list, pdf_file_path: str, metadata: dict,
    print_pdf_file_path: str | None = None,
) -> tuple[bool, str | None, str | None]:
    """Render HTML pages to a merged PDF inside an isolated process.

    Running WeasyPrint here gives it a fresh cairo/pango address space so
    concurrent PDF generations no longer share C-library state.

    When print_pdf_file_path is set, a second print-friendly PDF with
    downsampled images is written from the same rendered document. Failure
    to write it never fails the render — the third return element carries
    the error message instead.
    """
    try:
        import logging as _logging
        from weasyprint import HTML
        from pathlib import Path as _Path

        _logging.getLogger('weasyprint').setLevel(_logging.ERROR)
        _logging.getLogger('fontTools').setLevel(_logging.WARNING)

        _Path(pdf_file_path).parent.mkdir(parents=True, exist_ok=True)

        cache = {}
        docs = [HTML(string=html, base_url='/').render(image_cache=cache) for html in html_pages]
        all_pages = [page for doc in docs for page in doc.pages]

        if not docs or not all_pages:
            return False, "No pages were successfully rendered", None

        docs[0].copy(all_pages).write_pdf(pdf_file_path, metadata=metadata)

        print_error = None
        if print_pdf_file_path:
            try:
                # Image options are captured when images are decoded during
                # render(), not at write_pdf() time, so the print variant
                # needs its own render pass with its own image cache.
                print_options = {
                    'jpeg_quality': PRINT_JPEG_QUALITY,
                    'dpi': PRINT_DPI,
                    'optimize_images': True,
                }
                print_cache = {}
                print_docs = [
                    HTML(string=html, base_url='/').render(image_cache=print_cache, **print_options)
                    for html in html_pages
                ]
                print_pages = [page for doc in print_docs for page in doc.pages]
                print_docs[0].copy(print_pages).write_pdf(
                    print_pdf_file_path, metadata=metadata, **print_options
                )
            except Exception as exc:
                print_error = str(exc)
                _Path(print_pdf_file_path).unlink(missing_ok=True)

        return True, None, print_error
    except Exception as exc:
        return False, str(exc), None


@retry(
    exceptions=(Exception,),
    max_retries=settings.PDF_GENERATION_MAX_RETRIES,
    initial_delay=settings.PDF_GENERATION_RETRY_DELAY,
    max_delay=settings.PDF_GENERATION_MAX_DELAY,
    backoff_factor=2,
)
async def generate_pdf_from_html_pages(
    html_pages: List[str], safe_title: str, output_dir: Path,
    with_print_variant: bool = False,
) -> str:
    """
    Generate a PDF file from multiple HTML pages using WeasyPrint.

    Args:
        html_pages: List of HTML content for each page
        safe_title: Safe filename to use for the PDF
        output_dir: Directory where the PDF will be saved
        with_print_variant: Also write a smaller print-friendly PDF next to
            the main one ({safe_title}_print.pdf); best-effort only

    Returns:
        File path of the generated PDF
    """
    logger.info(f"Starting rendering of {len(html_pages)} pages")

    output_dir.mkdir(exist_ok=True)
    pdf_file_path = output_dir / f"{safe_title}.pdf"
    print_pdf_file_path = (
        output_dir / f"{safe_title}{PRINT_VARIANT_SUFFIX}.pdf"
        if with_print_variant else None
    )

    metadata = {
        "title": "Phonics Storybook",
        "author": "Phonics Maker",
        "creator": "Enzi",
        "producer": "Enzi",
        "creationDate": datetime.now().strftime("%Y-%m-%dT%H:%M:%S%z"),
        "modDate": datetime.now().strftime("%Y-%m-%dT%H:%M:%S%z"),
        "subject": "Educational Phonics Story",
        "keywords": "phonics,children,education,storybook",
    }

    pool = await _get_process_pool()
    loop = asyncio.get_running_loop()
    
    # Run the pool submission in executor to avoid blocking the event loop
    success, error, print_error = await loop.run_in_executor(
        None,
        lambda: pool.submit(
            _weasyprint_render_worker,
            html_pages,
            str(pdf_file_path),
            metadata,
            str(print_pdf_file_path) if print_pdf_file_path else None
        ).result()
    )

    if not success:
        raise RuntimeError(f"WeasyPrint subprocess failed: {error}")

    if print_error:
        logger.warning(f"Print-friendly PDF variant failed (continuing without it): {print_error}")

    logger.info(f"Combined PDF created successfully: {pdf_file_path}")
    return str(pdf_file_path)
