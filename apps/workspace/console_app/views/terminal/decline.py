"""
Loud WebSocket declines for the console terminal.

The console terminal FAILS CLOSED (operator mandate: exec strictly inside
the visitor's Apptainer instance — never a host shell). This module makes
those declines VISIBLE: every refusal sends a ❌ text frame naming the
failed stage and closes with a specific 4xxx code, instead of leaking a
bare 1011 with zero frames that shows the visitor nothing.
"""

import logging

logger = logging.getLogger(__name__)

# Established visitor-upsell phrasing (see terminal_provider.py,
# providers_api.py: "Sign up or log in to ...").
VISITOR_UPSELL = "Sign up or log in to get a full terminal."


async def send_decline(consumer, stage, exc=None, code=4010, detail=None):
    """Send a visible ❌ decline frame, then close with a specific code.

    Fail-closed and fail-LOUD: this never spawns any fallback execution
    path — it only makes the refusal visible and shaped.

    Args:
        consumer: TerminalConsumer instance (socket already accepted).
        stage: Human-readable pipeline stage that failed.
        exc: Exception that caused the decline. The full traceback is
            logged server-side; only the class name reaches the client.
        code: WebSocket close code. Existing taxonomy: 4010 for
            transient/retry failures, 4003 for permanent ones.
        detail: Optional client-visible reason overriding the class name.
    """
    reason = detail or (type(exc).__name__ if exc is not None else "unknown error")
    logger.error(
        f"Terminal decline at stage '{stage}': {reason} (close code {code})",
        exc_info=exc,
    )

    frame = f"\x1b[1;31m❌ Terminal unavailable — {stage}: {reason}\x1b[0m\r\n"
    user = getattr(consumer, "user", None)
    if user is not None and not getattr(user, "is_authenticated", False):
        frame += f"\x1b[1;33m→ {VISITOR_UPSELL}\x1b[0m\r\n"

    try:
        await consumer.send(text_data=frame)
    except Exception:
        logger.warning(
            f"Decline frame for stage '{stage}' could not be delivered "
            "(socket already gone?)",
            exc_info=True,
        )
    await consumer.close(code=code)


# EOF
