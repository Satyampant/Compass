"""Import every table so the metadata is complete."""

from app.kernel.models import Event, Job, Setting
from app.modules.capture.models import Capture, Note
from app.modules.day.models import DailyLog, Task
from app.modules.learning.models import LearningItem

__all__ = ["Capture", "DailyLog", "Event", "Job", "LearningItem", "Note", "Setting", "Task"]
