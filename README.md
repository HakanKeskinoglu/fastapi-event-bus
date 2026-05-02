# fastapi-event-bus

[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![CI](https://github.com/HakanKeskinoglu/fastapi-event-bus/actions/workflows/ci.yml/badge.svg)](https://github.com/HakanKeskinoglu/fastapi-event-bus/actions)

Lightweight, in-process event bus for FastAPI. No Celery, no Redis, no broker — just `emit` and `subscribe`.

> **⚠️ Single-process only.**  
> This library works in-process. If you run FastAPI with multiple Gunicorn workers (`--workers 2+`), an event emitted in Worker A will **not** reach a handler in Worker B. For cross-process or distributed messaging, use Celery, RabbitMQ, or Kafka instead.

---

## Why?

When your FastAPI app is a single process and you want to decouple components without the overhead of an external broker:

| Scenario | Tool |
|---|---|
| Single process, decouple components | ✅ **fastapi-event-bus** |
| Multiple workers / distributed | Celery + Redis / RabbitMQ |
| Fire-and-forget background tasks | FastAPI `BackgroundTasks` |

---

## Installation

```bash
pip install git+https://github.com/HakanKeskinoglu/fastapi-event-bus.git
```

---

## Quick Start

```python
from fastapi import FastAPI
from contextlib import asynccontextmanager
from fastapi_event_bus import EventBus

bus = EventBus()

@bus.on("user.created")
async def send_welcome_email(payload: dict):
    print(f"Sending welcome email to {payload['email']}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    async with bus.lifespan():
        yield

app = FastAPI(lifespan=lifespan)

@app.post("/users")
async def create_user():
    user = {"id": 1, "email": "hakan@example.com"}
    await bus.emit("user.created", user)
    return user
```

---

## Wildcard Subscriptions

Use `*` to match a single segment, `**` to match one or more segments.

```python
# Matches: user.created, user.deleted, user.updated
# Does NOT match: user.role.changed (two segments after "user")
@bus.on("user.*")
async def on_any_user_event(event: str, payload: dict):
    print(f"[{event}] {payload}")

# Matches: order.created, order.item.added, order.item.removed
@bus.on("order.**")
async def on_any_order_event(event: str, payload: dict):
    print(f"[{event}] {payload}")

# Matches: user.created, order.created, payment.created
@bus.on("*.created")
async def on_any_created(event: str, payload: dict):
    print(f"New entity created via [{event}]")
```

### Wildcard pattern reference

| Pattern | Matches | Does not match |
|---|---|---|
| `user.*` | `user.created`, `user.deleted` | `user.role.changed`, `user` |
| `user.**` | `user.created`, `user.role.changed` | `user`, `order.created` |
| `*.created` | `user.created`, `order.created` | `user.deleted` |
| `**` | everything | — |

> **Important:** Wildcard handlers **must** accept two parameters: `(event: str, payload: dict)`.  
> Exact match handlers accept only one: `(payload: dict)`.  
> Mixing these up will raise a standard Python `TypeError`.

---

## Multiple Handlers

Multiple handlers can be registered for the same pattern. All of them will be called concurrently via `asyncio.gather`. Order of execution is **not guaranteed**.

```python
@bus.on("user.created")
async def send_welcome_email(payload: dict): ...

@bus.on("user.created")
async def provision_storage(payload: dict): ...

@bus.on("user.created")
async def notify_admin(payload: dict): ...

# All three run concurrently on emit
await bus.emit("user.created", {"id": 1})
```

If one handler raises an exception, the others are **not affected**. The exception is logged and execution continues.

---

## FastAPI Lifespan Integration

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI

@asynccontextmanager
async def lifespan(app: FastAPI):
    async with bus.lifespan(graceful_timeout=5.0):
        yield

app = FastAPI(lifespan=lifespan)
```

`graceful_timeout` controls how long shutdown waits for in-flight handlers:
- `5.0` (default) — wait up to 5 seconds, then cancel remaining tasks
- `None` — wait indefinitely
- `0` — cancel immediately, don't wait

> **v1 note:** In this version `lifespan()` is a passthrough context manager. Graceful shutdown will become meaningful in v2 when fire-and-forget (`emit(background=True)`) is introduced.

---

## Debug Mode

```python
bus = EventBus(debug=True)
```

When `debug=True`, every `emit` call and every handler invocation is logged via `logging.debug`.

To see these logs, configure Python's logging before starting your app:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

---

## Configuration

```python
bus = EventBus(
    debug=False,         # Enable debug logging
    max_emit_depth=10,   # Max recursive emit depth before CircularEmitError
)
```

### Circular emit protection

If a handler emits an event that eventually triggers itself, `CircularEmitError` is raised once `max_emit_depth` is exceeded.

```python
@bus.on("a.triggered")
async def handler(payload: dict):
    await bus.emit("a.triggered", payload)  # CircularEmitError after depth 10
```

---

## Testing

Use `bus.clear()` in test teardown to reset all registered handlers between tests.

```python
import pytest
from fastapi_event_bus import EventBus

bus = EventBus()

@pytest.fixture(autouse=True)
def reset_bus():
    yield
    bus.clear()

@pytest.mark.asyncio
async def test_user_created_handler():
    results = []

    @bus.on("user.created")
    async def capture(payload: dict):
        results.append(payload)

    await bus.emit("user.created", {"id": 1})
    assert results == [{"id": 1}]
```

---

## API Reference

### `EventBus(debug=False, max_emit_depth=10)`

Creates a new event bus instance.

### `@bus.on(pattern: str)`

Registers an async handler for the given event pattern. Supports `*` and `**` wildcards.

### `await bus.emit(event: str, payload: dict)`

Emits an event. All matching handlers are called concurrently. Exceptions in handlers are logged and do not propagate.

### `bus.clear()`

Removes all registered handlers. Useful in tests.

### `bus.lifespan(graceful_timeout=5.0)`

Async context manager for FastAPI lifespan integration.

### `CircularEmitError`

Raised when `max_emit_depth` is exceeded during a recursive emit chain.

---

## Future Work

- `emit(background=True)` — fire-and-forget via `asyncio.create_task`, with true graceful shutdown
- Trie-based pattern matching for high handler-count scenarios
- Pydantic event type binding: `@bus.on("user.created", event_type=UserCreatedEvent)`
- `on_error` hook for custom error handling (e.g. Sentry integration)

---

## License

MIT