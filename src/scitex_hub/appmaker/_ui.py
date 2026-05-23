"""UI automation API — programmatic browser control for app navigation.

Generates step sequences compatible with the ``ui_action`` tool protocol.
Steps are executed by the browser via WebSocket (LLM AI panel) or can be
sent directly via the workspace WebSocket API.

Usage::

    from scitex_hub.appmaker import ui

    # Build step sequences
    steps = ui.navigate_to("/apps/scholar/")
    steps = ui.click_element("#save-button")
    steps = ui.switch_sidebar("writer")

    # Combine multiple steps
    demo = ui.chain(
        ui.navigate_to("/apps/writer/"),
        ui.highlight("#editor", message="This is the editor"),
        ui.click_element("#compile-btn"),
    )

    # Execute via WebSocket (requires active session)
    await ui.execute(steps, websocket=ws)
"""

from __future__ import annotations

import json
import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)


def navigate_to(url: str) -> list[dict[str, Any]]:
    """Navigate the browser to a URL."""
    return [{"action": "navigate", "url": url}]


def click_element(selector: str) -> list[dict[str, Any]]:
    """Click a DOM element by CSS selector."""
    return [{"action": "click", "selector": selector}]


def highlight(
    selector: str,
    *,
    message: str = "",
    position: str = "top",
) -> list[dict[str, Any]]:
    """Highlight a DOM element with an optional tooltip message."""
    step: dict[str, Any] = {
        "action": "highlight",
        "selector": selector,
    }
    if message:
        step["message"] = message
    if position != "top":
        step["position"] = position
    return [step]


def scroll_to(selector: str) -> list[dict[str, Any]]:
    """Scroll a DOM element into view."""
    return [{"action": "scroll", "selector": selector}]


def fill_input(selector: str, value: str) -> list[dict[str, Any]]:
    """Type text into an input element."""
    return [{"action": "fill", "selector": selector, "value": value}]


def clear_highlights() -> list[dict[str, Any]]:
    """Remove all highlight overlays."""
    return [{"action": "clear"}]


def switch_sidebar(app_name: str) -> list[dict[str, Any]]:
    """Switch the workspace sidebar to a specific app tab.

    Clicks the sidebar tab matching the app name.
    """
    return [{"action": "click", "selector": f'[data-module="{app_name}"]'}]


def send_notification(message: str) -> list[dict[str, Any]]:
    """Show a notification message (highlight the notification area)."""
    return [
        {
            "action": "highlight",
            "selector": "body",
            "message": message,
            "position": "top",
        },
    ]


def chain(*step_lists: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Combine multiple step sequences into one."""
    combined: list[dict[str, Any]] = []
    for steps in step_lists:
        combined.extend(steps)
    return combined


def to_ui_action(steps: list[dict[str, Any]], *, delay_ms: int = 900) -> dict[str, Any]:
    """Convert steps to the ``ui_action`` tool call format.

    This is the format expected by the LLM tool loop in mcp_client.py.
    """
    return {
        "steps": steps,
        "delay_ms": delay_ms,
    }


async def execute(
    steps: list[dict[str, Any]],
    *,
    websocket: Optional[Any] = None,
    delay_ms: int = 900,
) -> bool:
    """Execute UI steps via WebSocket.

    Args:
        steps: List of action step dicts.
        websocket: WebSocket connection (Django Channels or similar).
        delay_ms: Milliseconds between steps.

    Returns:
        True if steps were sent successfully.
    """
    if websocket is None:
        logger.warning("[ui] No websocket provided — steps not executed")
        return False

    payload = json.dumps(
        {
            "type": "ui_action",
            "steps": steps,
            "delay_ms": delay_ms,
        }
    )

    try:
        await websocket.send(payload)
        return True
    except Exception as exc:
        logger.error("[ui] Failed to send UI action: %s", exc)
        return False


# EOF
