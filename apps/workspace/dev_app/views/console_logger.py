"""
Console Logger View - Captures browser console logs to server file

Both views sit behind the /dev/ gate (``dev_app.access.dev_admin_only``):
developer tools must be explicitly enabled and the caller must be staff.
Every stored line is tagged with the uploader's user id, and a reader only
ever gets back its own lines -- never another account's.
"""

import json
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

# Setup dedicated console logger with rotation. Use settings.LOG_DIR
# (owned by config.settings.settings_logging, resolved via the
# runtime-state-db-layout convention -- see that module's docstring and
# incident hub-prod-outage-celery-log-permission). LOG_DIR is always
# defined by the time any settings module finishes loading, so no
# fallback default is needed here -- per project policy, a silent
# fallback would just mask a misconfigured settings module instead of
# failing loudly. Hard-coding ``settings.BASE_DIR / "logs"`` was
# creating a top-level ``logs/`` directory on every Django boot — a
# PS-102 §1 (no-top-level-forbidden-dir) violation flagged by the
# ecosystem audit gate.
_log_dir = Path(settings.LOG_DIR)
console_log_file = _log_dir / "console.log"
console_error_file = _log_dir / "console_error.log"
console_log_file.parent.mkdir(parents=True, exist_ok=True)

console_logger = logging.getLogger("browser_console")
console_logger.setLevel(logging.DEBUG)

# Handler 1: All logs to console.log (with rotation)
all_handler = RotatingFileHandler(
    console_log_file,
    maxBytes=5 * 1024 * 1024,  # 5MB
    backupCount=5,
)
all_handler.setLevel(logging.DEBUG)

# Handler 2: Errors/warnings only to console_error.log (with rotation)
error_handler = RotatingFileHandler(
    console_error_file,
    maxBytes=5 * 1024 * 1024,  # 5MB
    backupCount=5,
)
error_handler.setLevel(logging.WARNING)

# Format: [timestamp] LEVEL: message (file:line:col)
formatter = logging.Formatter(
    "[%(asctime)s] %(levelname)s: %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
)
all_handler.setFormatter(formatter)
error_handler.setFormatter(formatter)

console_logger.addHandler(all_handler)
console_logger.addHandler(error_handler)

# Prevent propagation to root logger
console_logger.propagate = False

# Each stored entry is one line tagged with the uploader's user id, so a
# reader only ever gets back the lines its own browser sent.
_OWNER_TAG = "uid={user_id} "
_DEFAULT_LINES = 500
_MAX_LINES = 5000
_LEVELS = {
    "log": logging.INFO,
    "info": logging.INFO,
    "warn": logging.WARNING,
    "warning": logging.WARNING,
    "error": logging.ERROR,
    "debug": logging.DEBUG,
}


def _owner_tag(user) -> str:
    return _OWNER_TAG.format(user_id=user.pk)


def _one_line(text) -> str:
    """Keep one entry per line so ownership filtering stays line-based."""
    return str(text).replace("\r", "\\r").replace("\n", "\\n")


def _is_owned_by(line: str, tag: str) -> bool:
    # Line format: "[timestamp] LEVEL: uid=<id> message"
    return line.partition(": ")[2].startswith(tag)


@require_http_methods(["GET"])
def get_console_logs(request):
    """Return the requesting user's own recent browser-console log lines."""
    try:
        max_lines = int(request.GET.get("lines", _DEFAULT_LINES))
    except ValueError:
        return JsonResponse(
            {"success": False, "error": "lines must be an integer"}, status=400
        )
    max_lines = max(1, min(max_lines, _MAX_LINES))

    own = []
    if console_log_file.exists():
        tag = _owner_tag(request.user)
        with open(console_log_file, "r", errors="replace") as f:
            own = [line for line in f if _is_owned_by(line, tag)]
    recent = own[-max_lines:]
    return JsonResponse(
        {
            "success": True,
            "logs": "".join(recent),
            "total_lines": len(own),
            "returned_lines": len(recent),
        }
    )


@require_http_methods(["POST"])
def log_console(request):
    """Store the requesting user's browser console logs.

    Expected payload::

        {"logs": [{"level": "log|info|warn|error", "message": "...",
                   "source": "file.js:123:45", "url": "https://..."}]}
    """
    try:
        data = json.loads(request.body)
    except (ValueError, UnicodeDecodeError):
        return JsonResponse({"status": "error", "message": "invalid JSON"}, status=400)
    logs = data.get("logs") if isinstance(data, dict) else None
    if not isinstance(logs, list):
        return JsonResponse(
            {"status": "error", "message": "logs must be a list"}, status=400
        )

    tag = _owner_tag(request.user)
    logged = 0
    for entry in logs:
        if not isinstance(entry, dict):
            continue
        message = tag + _one_line(entry.get("message", ""))
        if entry.get("source"):
            message += f" ({_one_line(entry['source'])})"
        if entry.get("url"):
            message += f" | {_one_line(entry['url'])}"
        level = _LEVELS.get(str(entry.get("level", "log")).lower(), logging.INFO)
        console_logger.log(level, message)
        logged += 1

    return JsonResponse({"status": "ok", "logged": logged})
