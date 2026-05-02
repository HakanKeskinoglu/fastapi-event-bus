"""
Tests for EventBus core.
"""
import logging
import pytest
from fastapi_event_bus import EventBus, CircularEmitError


@pytest.fixture
def bus():
    b = EventBus()
    yield b
    b.clear()


@pytest.fixture
def debug_bus():
    b = EventBus(debug=True)
    yield b
    b.clear()


class TestSubscribeAndEmit:
    @pytest.mark.asyncio
    async def test_exact_handler_called(self, bus):
        received = []

        @bus.on("user.created")
        async def handler(payload: dict):
            received.append(payload)

        await bus.emit("user.created", {"id": 1})
        assert received == [{"id": 1}]

    @pytest.mark.asyncio
    async def test_exact_handler_not_called_for_other_event(self, bus):
        received = []

        @bus.on("user.created")
        async def handler(payload: dict):
            received.append(payload)

        await bus.emit("user.deleted", {"id": 1})
        assert received == []

    @pytest.mark.asyncio
    async def test_wildcard_handler_called(self, bus):
        received = []

        @bus.on("user.*")
        async def handler(event: str, payload: dict):
            received.append((event, payload))

        await bus.emit("user.created", {"id": 1})
        assert received == [("user.created", {"id": 1})]

    @pytest.mark.asyncio
    async def test_wildcard_receives_correct_event_name(self, bus):
        events = []

        @bus.on("user.*")
        async def handler(event: str, payload: dict):
            events.append(event)

        await bus.emit("user.deleted", {})
        assert events == ["user.deleted"]

    @pytest.mark.asyncio
    async def test_multiple_handlers_same_pattern_all_called(self, bus):
        calls = []

        @bus.on("order.created")
        async def h1(payload: dict):
            calls.append("h1")

        @bus.on("order.created")
        async def h2(payload: dict):
            calls.append("h2")

        @bus.on("order.created")
        async def h3(payload: dict):
            calls.append("h3")

        await bus.emit("order.created", {})
        assert sorted(calls) == ["h1", "h2", "h3"]

    @pytest.mark.asyncio
    async def test_emit_no_subscribers_is_noop(self, bus):
        # Should not raise
        await bus.emit("ghost.event", {"data": "x"})

    @pytest.mark.asyncio
    async def test_both_exact_and_wildcard_triggered(self, bus):
        calls = []

        @bus.on("user.created")
        async def exact(payload: dict):
            calls.append("exact")

        @bus.on("user.*")
        async def wildcard(event: str, payload: dict):
            calls.append("wildcard")

        await bus.emit("user.created", {})
        assert sorted(calls) == ["exact", "wildcard"]


class TestExceptionIsolation:
    @pytest.mark.asyncio
    async def test_failing_handler_does_not_stop_others(self, bus):
        calls = []

        @bus.on("test.event")
        async def failing(payload: dict):
            raise ValueError("boom")

        @bus.on("test.event")
        async def succeeding(payload: dict):
            calls.append("ok")

        # Should not raise
        await bus.emit("test.event", {})
        assert calls == ["ok"]

    @pytest.mark.asyncio
    async def test_exception_is_logged(self, bus, caplog):
        @bus.on("test.event")
        async def failing(payload: dict):
            raise RuntimeError("test error")

        with caplog.at_level(logging.ERROR):
            await bus.emit("test.event", {})

        assert any("test error" in r.message for r in caplog.records)


class TestCircularEmitGuard:
    @pytest.mark.asyncio
    async def test_circular_emit_raises(self, bus):
        @bus.on("loop.event")
        async def looping(payload: dict):
            await bus.emit("loop.event", payload)

        with pytest.raises(CircularEmitError):
            await bus.emit("loop.event", {})

    @pytest.mark.asyncio
    async def test_circular_error_contains_event_name(self, bus):
        @bus.on("loop.event")
        async def looping(payload: dict):
            await bus.emit("loop.event", payload)

        with pytest.raises(CircularEmitError) as exc_info:
            await bus.emit("loop.event", {})

        assert "loop.event" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_custom_depth_limit(self):
        bus = EventBus(max_emit_depth=3)
        call_count = [0]

        @bus.on("deep.event")
        async def looping(payload: dict):
            call_count[0] += 1
            await bus.emit("deep.event", payload)

        with pytest.raises(CircularEmitError):
            await bus.emit("deep.event", {})

        assert call_count[0] == 3

    @pytest.mark.asyncio
    async def test_depth_resets_after_emit(self, bus):
        results = []

        @bus.on("safe.event")
        async def handler(payload: dict):
            results.append(1)

        await bus.emit("safe.event", {})
        await bus.emit("safe.event", {})
        assert results == [1, 1]
        assert bus._emit_depth == 0


class TestClear:
    @pytest.mark.asyncio
    async def test_clear_removes_all_handlers(self, bus):
        received = []

        @bus.on("user.created")
        async def handler(payload: dict):
            received.append(1)

        bus.clear()
        await bus.emit("user.created", {})
        assert received == []

    def test_clear_on_empty_bus_does_not_raise(self, bus):
        bus.clear()  # Should be idempotent


class TestDebugMode:
    @pytest.mark.asyncio
    async def test_debug_logs_emit(self, debug_bus, caplog):
        @debug_bus.on("ping")
        async def handler(payload: dict):
            pass

        with caplog.at_level(logging.DEBUG):
            await debug_bus.emit("ping", {})

        assert any("ping" in r.message for r in caplog.records)

    def test_debug_logs_registration(self, caplog):
        bus = EventBus(debug=True)

        with caplog.at_level(logging.DEBUG):
            @bus.on("user.created")
            async def handler(payload: dict):
                pass

        assert any("user.created" in r.message for r in caplog.records)