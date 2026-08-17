# phonics_maker/pdf_generation/file_utils.py

import re
from pathlib import Path
from app.core.config.logger import logger


def make_filesystem_safe(title: str) -> str:
    """
    Convert a string into a filesystem-safe filename.

    Args:
        title: The string to convert

    Returns:
        A safe filename
    """
    # Replace spaces with underscores
    safe_name = title.replace(" ", "_")

    # Remove invalid characters
    safe_name = re.sub(r'[\\/*?:"<>|]', "", safe_name)

    # Limit length to 100 characters
    safe_name = safe_name[:100]

    return safe_name


def ensure_directory_exists(directory_path: Path) -> None:
    """
    Create a directory if it doesn't exist.

    Args:
        directory_path: Path of the directory to create
    """
    directory_path.mkdir(exist_ok=True, parents=True)

def get_task_temp_dir(temp_dir: str, task_id: str) -> Path:
    """Get or create a task-specific temp directory"""
    task_dir = temp_dir / task_id
    task_dir.mkdir(exist_ok=True)
    return task_dir

def cleanup_task_temp_dir(task_temp_dir: Path):
    """Clean up only this task's temp files"""
    try:
        for file in task_temp_dir.glob("*"):
            try:
                if file.is_file():
                    file.unlink()
            except Exception as e:
                logger.error(f"Error deleting temp file {file}: {str(e)}")

        # Remove the directory itself
        try:
            task_temp_dir.rmdir()
        except OSError:
            pass  # Directory not empty or already deleted

    except Exception as e:
        logger.error(f"Error cleaning up task temp dir: {str(e)}")
