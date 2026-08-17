# core/config/logger.py

import sys
from loguru import logger
from app.core.config.config import settings
import uuid
from contextvars import ContextVar

# Task ID context variable
task_id_ctx = ContextVar("task_id", default="")

# Function to set task ID for the current context
def set_task_id(task_id=None):
    """Set a task ID for the current context or generate a new one if not provided"""
    if task_id is None:
        task_id = str(uuid.uuid4())
    task_id_ctx.set(task_id)
    return task_id

# Function to get task ID from current context
def get_task_id():
    """Get the task ID for the current context"""
    return task_id_ctx.get()

# Remove default logger
logger.remove()

# Configure logging format with task ID
log_format = (
    "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
    "<level>{level: <8}</level> | "
    "<magenta>{extra[task_id]}</magenta> | "
    "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
    "<level>{message}</level>"
)

# Add contextualized logger with task_id
class TaskLogger:
    def __init__(self, logger_instance):
        self._logger = logger_instance.bind(task_id="")
    
    def _get_contextualized_logger(self):
        task_id = get_task_id()
        return self._logger.bind(task_id=task_id)
    
    def debug(self, message, *args, **kwargs):
        self._get_contextualized_logger().debug(message, *args, **kwargs)
    
    def info(self, message, *args, **kwargs):
        self._get_contextualized_logger().info(message, *args, **kwargs)
    
    def warning(self, message, *args, **kwargs):
        self._get_contextualized_logger().warning(message, *args, **kwargs)
    
    def error(self, message, *args, **kwargs):
        self._get_contextualized_logger().error(message, *args, **kwargs)
    
    def critical(self, message, *args, **kwargs):
        self._get_contextualized_logger().critical(message, *args, **kwargs)
    
    def exception(self, message, *args, **kwargs):
        self._get_contextualized_logger().exception(message, *args, **kwargs)

# Add console logger
logger.add(sys.stderr, format=log_format, level="DEBUG", colorize=True)

# Add file logger for production
if settings.ENVIRONMENT == "production" or settings.ENVIRONMENT == "development":
    logger.add(
        "logs/phonicsmaker.log",
        rotation="10 MB",  # Rotate log files every 10 MB
        retention="30 days",  # Keep logs for 30 days
        compression="zip",  # Compress old log files
        level="INFO",  # Log only INFO and above in production
        format=log_format,
    )
    
# Export task-aware logger for use in other modules
logger = TaskLogger(logger)