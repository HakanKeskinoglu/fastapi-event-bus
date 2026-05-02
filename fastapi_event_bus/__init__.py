"""fastapi-event-bus — lightweight in-process event bus for FastAPI."""

from .bus import EventBus
from .exceptions import CircularEmitError

__all__ = ["EventBus", "CircularEmitError"]
__version__ = "0.1.0"