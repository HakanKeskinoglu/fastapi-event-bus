"""
Integration tests — EventBus inside a real FastAPI app.

Uses FastAPI's TestClient with lifespan to simulate
production usage as closely as possible.
"""
import pytest
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.testclient import TestClient

from fastapi_event_bus import EventBus


# ------------------------------------------------------------------ #
# Helpers
# ------------------------------------------------------------------ #

def make_app(bus: EventBus) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        async with bus.lifespan():
            yield

    app = FastAPI(lifespan=lifespan)
    return app


# ------------------------------------------------------------------ #
# Tests
# ------------------------------------------------------------------ #

class TestBasicIntegration:
    def test_handler_called_on_request(self):
        bus = EventBus()
        received = []

        @bus.on("order.placed")
        async def on_order(payload: dict):
            received.append(payload)

        app = make_app(bus)

        @app.post("/orders")
        async def place_order():
            await bus.emit("order.placed", {"item": "book"})
            return {"ok": True}

        with TestClient(app) as client:
            resp = client.post("/orders")
            assert resp.status_code == 200
            assert received == [{"item": "book"}]

    def test_multiple_handlers_all_called(self):
        bus = EventBus()
        log = []

        @bus.on("payment.received")
        async def send_receipt(payload: dict):
            log.append("receipt")

        @bus.on("payment.received")
        async def update_balance(payload: dict):
            log.append("balance")

        app = make_app(bus)

        @app.post("/pay")
        async def pay():
            await bus.emit("payment.received", {"amount": 50})
            return {"ok": True}

        with TestClient(app) as client:
            client.post("/pay")
            assert sorted(log) == ["balance", "receipt"]

    def test_wildcard_handler_receives_event_name(self):
        bus = EventBus()
        events = []

        @bus.on("user.*")
        async def on_any_user(event: str, payload: dict):
            events.append(event)

        app = make_app(bus)

        @app.post("/users/create")
        async def create():
            await bus.emit("user.created", {"id": 1})
            return {}

        @app.post("/users/delete")
        async def delete():
            await bus.emit("user.deleted", {"id": 1})
            return {}

        with TestClient(app) as client:
            client.post("/users/create")
            client.post("/users/delete")
            assert events == ["user.created", "user.deleted"]

    def test_no_handler_does_not_break_endpoint(self):
        bus = EventBus()
        app = make_app(bus)

        @app.get("/ping")
        async def ping():
            await bus.emit("unhandled.event", {})
            return {"pong": True}

        with TestClient(app) as client:
            resp = client.get("/ping")
            assert resp.status_code == 200
            assert resp.json() == {"pong": True}


class TestExceptionIsolationInRequest:
    def test_failing_handler_does_not_break_response(self):
        bus = EventBus()
        good_calls = []

        @bus.on("checkout.completed")
        async def failing(payload: dict):
            raise ValueError("payment service down")

        @bus.on("checkout.completed")
        async def succeeding(payload: dict):
            good_calls.append(1)

        app = make_app(bus)

        @app.post("/checkout")
        async def checkout():
            await bus.emit("checkout.completed", {"cart_id": "abc"})
            return {"status": "ok"}

        with TestClient(app) as client:
            resp = client.post("/checkout")
            assert resp.status_code == 200
            assert good_calls == [1]


class TestLifespan:
    def test_lifespan_starts_and_stops_cleanly(self):
        bus = EventBus()
        lifecycle = []

        @asynccontextmanager
        async def lifespan(app: FastAPI):
            lifecycle.append("start")
            async with bus.lifespan(graceful_timeout=1.0):
                yield
            lifecycle.append("stop")

        app = FastAPI(lifespan=lifespan)

        @app.get("/")
        async def root():
            return {}

        with TestClient(app) as client:
            client.get("/")

        assert lifecycle == ["start", "stop"]

    def test_lifespan_zero_timeout(self):
        bus = EventBus()

        @asynccontextmanager
        async def lifespan(app: FastAPI):
            async with bus.lifespan(graceful_timeout=0):
                yield

        app = FastAPI(lifespan=lifespan)

        @app.get("/")
        async def root():
            return {}

        with TestClient(app) as client:
            resp = client.get("/")
            assert resp.status_code == 200