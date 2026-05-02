"""Custom exceptions for fastapi-event-bus."""


class CircularEmitError(RuntimeError):
    """Raised when emit depth exceeds max_emit_depth."""

    def __init__(self, event: str, depth: int) -> None:
        self.event = event
        self.depth = depth
        super().__init__(
            f"Circular emit detected: event={event!r} reached depth={depth}. "
            "A handler is likely emitting the same event it handles."
        )