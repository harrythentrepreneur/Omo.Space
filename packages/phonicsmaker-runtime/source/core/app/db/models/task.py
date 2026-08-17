# core/models/task.py
from enum import Enum


class TaskStatus(str, Enum):
    QUEUED = "QUEUED"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    DRAFT_READY = "DRAFT_READY"