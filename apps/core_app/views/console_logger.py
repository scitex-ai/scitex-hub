"""
Console Logger View - Captures browser console logs to server file
"""

import json
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

# Setup dedicated console logger with rotation
console_log_file = Path(settings.BASE_DIR) / "logs" / "console.log"
console_error_file = Path(settings.BASE_DIR) / "logs" / "console_error.log"
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


@require_http_methods(["GET"])
def get_console_logs(request):
    """
    Return the console logs file content for debug snapshots.
    Only available in DEBUG mode.
    """
    if not settings.DEBUG:
        return JsonResponse({"error": "Only available in DEBUG mode"}, status=403)

    try:
        if console_log_file.exists():
            # Read last N lines (default 500)
            max_lines = int(request.GET.get("lines", 500))
            with open(console_log_file, "r") as f:
                lines = f.readlines()
                # Get last N lines
                recent_lines = lines[-max_lines:]
                content = "".join(recent_lines)
                return JsonResponse({
                    "success": True,
                    "logs": content,
                    "total_lines": len(lines),
                    "returned_lines": len(recent_lines),
                })
        else:
            return JsonResponse({
                "success": True,
                "logs": "No console logs file found.",
                "total_lines": 0,
                "returned_lines": 0,
            })
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=500)


@csrf_exempt  # Allow from dev frontend without CSRF
@require_http_methods(["POST"])
def log_console(request):
    """
    Receive browser console logs and write to ./logs/console.log

    Expected payload:
    {
        "logs": [
            {
                "level": "log|info|warn|error",
                "message": "Console message",
                "source": "file.js:123:45",
                "timestamp": 1234567890.123,
                "url": "http://localhost:8000/writer/"
            },
            ...
        ]
    }
    """
    try:
        data = json.loads(request.body)
        logs = data.get("logs", [])

        # Map console levels to logging levels
        level_map = {
            "log": logging.INFO,
            "info": logging.INFO,
            "warn": logging.WARNING,
            "warning": logging.WARNING,
            "error": logging.ERROR,
            "debug": logging.DEBUG,
        }

        for log_entry in logs:
            level = log_entry.get("level", "log").lower()
            message = log_entry.get("message", "")
            source = log_entry.get("source", "")
            url = log_entry.get("url", "")

            # Format log message
            log_msg = f"{message}"
            if source:
                log_msg += f" ({source})"
            if url:
                log_msg += f" | {url}"

            log_level = level_map.get(level, logging.INFO)
            console_logger.log(log_level, log_msg)

        return JsonResponse({"status": "ok", "logged": len(logs)})

    except Exception as e:
        console_logger.error(f"Failed to process console logs: {e}")
        return JsonResponse({"status": "error", "message": str(e)}, status=500)
