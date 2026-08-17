# phonics_maker/pdf_generation/html_renderer.py

import jinja2
from pathlib import Path
from typing import Dict, Any
from app.core.config.logger import logger
from app.core.utils.retry import retry
from app.core.config.config import settings


class HTMLRenderer:
    """
    Handles HTML template rendering using Jinja2.
    """

    def __init__(self, template_dir: Path):
        """
        Initialize the HTML renderer with a template directory.

        Args:
            template_dir: Path to the directory containing Jinja2 templates
        """
        self.template_env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(template_dir),
            autoescape=True,
        )

    @retry(
        exceptions=(Exception,),
        max_retries=settings.PDF_PROCESS_MAX_RETRIES,
        initial_delay=settings.PDF_PROCESS_RETRY_DELAY,
        max_delay=settings.PDF_PROCESS_MAX_DELAY,
        backoff_factor=1.5,
    )
    async def render_template(
        self, template_name: str, template_data: Dict[str, Any]
    ) -> str:
        """
        Render an HTML template with the provided data.

        Args:
            template_name: Name of the template file
            template_data: Data to render in the template

        Returns:
            Rendered HTML content as a string
        """
        try:
            template = self.template_env.get_template(template_name)
            return template.render(**template_data)
        except Exception as e:
            logger.error(f"Error rendering HTML template {template_name}: {str(e)}")
            raise e
