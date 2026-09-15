#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""System context for the floating dock chat: the page under it plus the hub's apps.

The floating chat is an iframe of /chat/?embed=1&ctx_path=...&ctx_title=..., so
the assistant must answer about the page the user is ON, not the chat page.
The app list is read mechanically from the module registry (each app's
manifest.json: label, url, ai_hint), never hand-written.
"""

from __future__ import annotations

import re
from functools import lru_cache

MAX_PATH = 200
MAX_TITLE = 120
MAX_APP_LINE = 160
MAX_APPS_CHARS = 5000  # about 1.2k tokens

_CONTROL = re.compile(r"[\x00-\x1f\x7f<>`]")


def _clean(value, limit: int) -> str:
    text = _CONTROL.sub(" ", str(value or ""))
    return " ".join(text.split())[:limit]


def _app_for_path(path: str) -> str:
    from apps.infra.workspace_app.registry import get_all_modules

    best, best_len = "", 0
    for module in get_all_modules():
        url = module.get_url().rstrip("/")
        if url and (path == url or path.startswith(url + "/")) and len(url) > best_len:
            best, best_len = module.name, len(url)
    return best


@lru_cache(maxsize=1)
def hub_apps_summary() -> str:
    """One line per public app from its manifest; label only when it has no hint."""
    from apps.infra.workspace_app.registry import get_all_modules

    lines = []
    for m in get_all_modules():
        if m.visibility != "public":
            continue
        hint = _clean(m.ai_hint, MAX_APP_LINE)
        lines.append(f"- {m.label} ({m.get_url()})" + (f": {hint}" if hint else ""))
    text = "\n".join(lines)[:MAX_APPS_CHARS]
    try:
        from apps.workspace.docs_app.views import DOCS_PAGES

        howtos = [p["slug"] for p in DOCS_PAGES if p["slug"].startswith("howto-")]
    except Exception:
        howtos = []
    docs = "How-to guides: /apps/docs/" + (f" ({', '.join(howtos)})" if howtos else "")
    return f"## SciTeX Cloud apps\n{text}\n{docs}"


def page_context_prompt(context: dict) -> str:
    """The prefix naming the page under the floating chat; empty without ctx_path."""
    path = _clean(context.get("ctx_path"), MAX_PATH)
    if not path.startswith("/"):
        return ""
    title = _clean(context.get("ctx_title"), MAX_TITLE) or path
    app = _app_for_path(path)
    where = f"The user is on {title} ({path})" + (f", app {app}" if app else "")
    return (
        "You are the SciTeX Cloud guide and know how to use the whole platform. "
        f"{where}. Help them with what they can do on this page.\n\n"
        f"{hub_apps_summary()}\n\n"
    )


# EOF
