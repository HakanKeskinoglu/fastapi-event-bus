"""
Handler wrapper for event bus subscribers.

Abstracts the difference between exact match and wildcard handlers:
- Exact match: async def handler(payload: dict)
- Wildcard:    async def handler(event: str, payload: dict)
"""
from __future__ import annotations

from typing import Any, Callable, Coroutine


AsyncCallable = Callable[..., Coroutine[Any, Any, None]]


class Handler:
    """Wraps an async subscriber function with its pattern metadata."""

    def __init__(self, fn: AsyncCallable, pattern: str, is_wildcard: bool) -> None:
        self.fn = fn
        self.pattern = pattern
        self.is_wildcard = is_wildcard

    async def __call__(self, event: str, payload: dict) -> None:
        """
        Call the underlying function with the appropriate signature.

        Wildcard handlers receive (event, payload).
        Exact match handlers receive (payload,) only.
        """
        if self.is_wildcard:
            await self.fn(event, payload)
        else:
            await self.fn(payload)

    def __repr__(self) -> str:
        kind = "wildcard" if self.is_wildcard else "exact"
        return f"<Handler pattern={self.pattern!r} kind={kind} fn={self.fn.__name__!r}>"
        