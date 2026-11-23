"""Import every table so the metadata is complete."""

from app.kernel.models import Event, Job, Setting
from app.modules.capture.models import Capture, Note
from app.modules.day.models import DailyLog, Task, TimeBlock
from app.modules.learning.models import LearningItem
from app.modules.notify.models import Notification
from app.modules.planning.models import Goal, KeyResult
from app.modules.review.models import DayStats, Review

__all__ = [
    "Capture",
    "DailyLog",
    "Event",
    "Goal",
    "Job",
    "KeyResult",
    "LearningItem",
    "Note",
    "DayStats",
    "Review",
    "Notification",
    "Setting",
    "Task",
    "TimeBlock",
]
