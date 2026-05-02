"""
Event definitions and handlers for the user service example.

All handlers are registered here and imported in main.py
so the bus is fully wired before the app starts.
"""
import logging
from fastapi_event_bus import EventBus

logger = logging.getLogger(__name__)

bus = EventBus(debug=True)


# ------------------------------------------------------------------ #
# Exact match handlers
# ------------------------------------------------------------------ #

@bus.on("user.created")
async def send_welcome_email(payload: dict) -> None:
    logger.info("📧 Sending welcome email to %s", payload["email"])


@bus.on("user.created")
async def provision_storage(payload: dict) -> None:
    logger.info("💾 Provisioning storage for user id=%s", payload["id"])


@bus.on("user.deleted")
async def cleanup_storage(payload: dict) -> None:
    logger.info("🗑️  Cleaning up storage for user id=%s", payload["id"])


# ------------------------------------------------------------------ #
# Wildcard handlers
# ------------------------------------------------------------------ #

@bus.on("user.*")
async def audit_log(event: str, payload: dict) -> None:
    """Log every user event for audit trail."""
    logger.info("📋 AUDIT [%s] %s", event, payload)


@bus.on("user.**")
async def metrics(event: str, payload: dict) -> None:
    """Increment metrics counter for any user-related event."""
    logger.info("📊 METRIC user_events_total{event=%r} +1", event)