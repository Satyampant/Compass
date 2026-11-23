"""Import every module that registers job handlers or bot handlers."""

from app.kernel import backup  # noqa: F401
from app.modules.autopilot import brief, cycle, reminders, resurface  # noqa: F401
from app.modules.capture import enrich, telegram  # noqa: F401
from app.modules.day import blocks, meetings  # noqa: F401
from app.modules.day import telegram as day_telegram  # noqa: F401
from app.modules.learning import telegram as learning_telegram  # noqa: F401
from app.modules.review import rollup  # noqa: F401
from app.modules.review import service as review_service  # noqa: F401
