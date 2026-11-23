"""Import every module that registers job handlers or bot handlers."""

from app.modules.autopilot import brief, resurface  # noqa: F401
from app.modules.capture import enrich, telegram  # noqa: F401
from app.modules.day import telegram as day_telegram  # noqa: F401
from app.modules.learning import telegram as learning_telegram  # noqa: F401
