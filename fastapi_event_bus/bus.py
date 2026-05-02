"""
EventBus — lightweight in-process event bus for FastAPI.

Usage:
    bus = EventBus()

    @bus.on("user.created")
    async def handle(payload: dict): ...

    await bus.emit("user.created", {"id": 1})
"""
from __future__ import annotations

import asyncio
import logging
from collections import defaultdict
from contextlib import asynccontextmanager
from typing import AsyncIterator, Callable

from .exceptions import CircularEmitError
from .handler import Handler, AsyncCallable
from .matching import matches
from typing import Any, AsyncIterator, Callable

logger = logging.getLogger(__name__)


class EventBus:
    def __init__(
        self,
        debug: bool = False,
        max_emit_depth: int = 10,
    ) -> None:
        self._debug = debug
        self._max_emit_depth = max_emit_depth
        self._registry: dict[str, list[Handler]] = defaultdict(list)
        self._emit_depth: int = 0

    # ------------------------------------------------------------------ #
    # Registration
    # ------------------------------------------------------------------ #

    def on(self, pattern: str) -> Callable[[AsyncCallable], AsyncCallable]:
        """Decorator that registers an async handler for the given pattern."""
        is_wildcard = "*" in pattern

        def decorator(fn: AsyncCallable) -> AsyncCallable:
            handler = Handler(fn=fn, pattern=pattern, is_wildcard=is_wildcard)
            self._registry[pattern].append(handler)
            if self._debug:
                logger.debug("Registered handler: %r", handler)
            return fn

        return decorator

    # ------------------------------------------------------------------ #
    # Emit
    # ------------------------------------------------------------------ #

    async def emit(self, event: str, payload: dict[str, Any]) -> None:
        """
        Emit an event. All matching handlers run concurrently.

        Exceptions raised by individual handlers are logged and do not
        propagate — other handlers continue executing unaffected.

        Raises:
            CircularEmitError: if emit depth exceeds max_emit_depth.
        """
        self._emit_depth += 1

        try:
            if self._emit_depth > self._max_emit_depth:
                raise CircularEmitError(event=event, depth=self._emit_depth)

            if self._debug:
                logger.debug("emit event=%r payload=%r depth=%d", event, payload, self._emit_depth)

            handlers = self._resolve_handlers(event)

            if not handlers:
                if self._debug:
                    logger.debug("No handlers matched event=%r", event)
                return

            results = await asyncio.gather(
                *[h(event, payload) for h in handlers],
                return_exceptions=True,
            )

            for handler, result in zip(handlers, results):
                if isinstance(result, CircularEmitError):
                    raise result
                if isinstance(result, BaseException):
                    logger.error(
                        "Handler %r raised an exception for event=%r: %s",
                        handler,
                        event,
                        result,
                        exc_info=result,
                    )
        finally:
            self._emit_depth -= 1

    def _resolve_handlers(self, event: str) -> list[Handler]:
        """Return all handlers whose pattern matches the given event."""
        matched: list[Handler] = []
        for pattern, handlers in self._registry.items():
            if matches(pattern, event):
                matched.extend(handlers)
        return matched

    # ------------------------------------------------------------------ #
    # Utilities
    # ------------------------------------------------------------------ #

    def clear(self) -> None:
        """Remove all registered handlers. Useful in tests."""
        self._registry.clear()
        if self._debug:
            logger.debug("EventBus cleared.")

    # ------------------------------------------------------------------ #
    # Lifespan
    # ------------------------------------------------------------------ #

    @asynccontextmanager
    async def lifespan(self, graceful_timeout: float | None = 5.0) -> AsyncIterator[None]:
        """
        Async context manager for FastAPI lifespan integration.

        v1: passthrough — graceful shutdown becomes meaningful in v2
        when fire-and-forget (emit(background=True)) is introduced.

        Args:
            graceful_timeout: seconds to wait for in-flight tasks on shutdown.
                              None = wait indefinitely. 0 = don't wait.
        """
        yield