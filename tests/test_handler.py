"""
Tests for Handler wrapper.
"""
import pytest
from fastapi_event_bus.handler import Handler


class TestExactHandler:
    @pytest.mark.asyncio
    async def test_exact_handler_receives_payload_only(self):
        received = []

        async def fn(payload: dict):
            received.append(payload)

        handler = Handler(fn=fn, pattern="user.created", is_wildcard=False)
        await handler(event="user.created", payload={"id": 1})

        assert received == [{"id": 1}]

    @pytest.mark.asyncio
    async def test_exact_handler_does_not_receive_event_name(self):
        received = []

        async def fn(payload: dict):
            received.append(payload)

        handler = Handler(fn=fn, pattern="user.created", is_wildcard=False)
        await handler(event="user.created", payload={"id": 2})

        # Only one argument passed — if event name were passed, fn would raise TypeError
        assert len(received) == 1

    @pytest.mark.asyncio
    async def test_exact_handler_wrong_signature_raises(self):
        async def fn(event: str, payload: dict):
            pass

        handler = Handler(fn=fn, pattern="user.created", is_wildcard=False)

        with pytest.raises(TypeError):
            await handler(event="user.created", payload={})


class TestWildcardHandler:
    @pytest.mark.asyncio
    async def test_wildcard_handler_receives_event_and_payload(self):
        received = []

        async def fn(event: str, payload: dict):
            received.append((event, payload))

        handler = Handler(fn=fn, pattern="user.*", is_wildcard=True)
        await handler(event="user.created", payload={"id": 1})

        assert received == [("user.created", {"id": 1})]

    @pytest.mark.asyncio
    async def test_wildcard_handler_event_name_matches_actual_event(self):
        captured_event = []

        async def fn(event: str, payload: dict):
            captured_event.append(event)

        handler = Handler(fn=fn, pattern="user.*", is_wildcard=True)
        await handler(event="user.deleted", payload={})

        assert captured_event == ["user.deleted"]

    @pytest.mark.asyncio
    async def test_wildcard_handler_wrong_signature_raises(self):
        async def fn(payload: dict):
            pass

        handler = Handler(fn=fn, pattern="user.*", is_wildcard=True)

        with pytest.raises(TypeError):
            await handler(event="user.created", payload={})


class TestHandlerRepr:
    def test_exact_repr(self):
        async def my_handler(payload: dict): pass

        handler = Handler(fn=my_handler, pattern="user.created", is_wildcard=False)
        assert "exact" in repr(handler)
        assert "user.created" in repr(handler)
        assert "my_handler" in repr(handler)

    def test_wildcard_repr(self):
        async def my_handler(event: str, payload: dict): pass

        handler = Handler(fn=my_handler, pattern="user.*", is_wildcard=True)
        assert "wildcard" in repr(handler)
        assert "user.*" in repr(handler)