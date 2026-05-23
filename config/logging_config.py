"""
Logging configuration for SciTeX Hub.

Provides structured logging with file rotation for:
- console.log: All API activity and errors
- errors.log: Errors only
- git.log: Git operations
- compilation.log: LaTeX compilation
"""

import os
from pathlib import Path

# Base directory
BASE_DIR = Path(__file__).resolve().parent.parent
LOGS_DIR = BASE_DIR / "logs"

# Ensure logs directory exists
LOGS_DIR.mkdir(exist_ok=True)

# Logging configuration
LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{asctime} [{levelname}] {name}: {message}",
            "style": "{",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
        "simple": {
            "format": "{levelname} {message}",
            "style": "{",
        },
    },
    "handlers": {
        # Console output (development)
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "simple",
            "level": "INFO",
        },
        # Main console.log file (all API activity)
        "console_file": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": str(LOGS_DIR / "console.log"),
            "maxBytes": 10485760,  # 10MB
            "backupCount": 5,
            "formatter": "verbose",
            "level": "INFO",
        },
        # Errors only
        "error_file": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": str(LOGS_DIR / "errors.log"),
            "maxBytes": 10485760,  # 10MB
            "backupCount": 5,
            "formatter": "verbose",
            "level": "ERROR",
        },
        # Git operations
        "git_file": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": str(LOGS_DIR / "git.log"),
            "maxBytes": 5242880,  # 5MB
            "backupCount": 3,
            "formatter": "verbose",
            "level": "INFO",
        },
        # LaTeX compilation
        "compilation_file": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": str(LOGS_DIR / "compilation.log"),
            "maxBytes": 10485760,  # 10MB
            "backupCount": 3,
            "formatter": "verbose",
            "level": "INFO",
        },
    },
    "loggers": {
        # Main console logger (for error cascading)
        "scitex.console": {
            "handlers": ["console_file", "console"],
            "level": "INFO",
            "propagate": False,
        },
        # Error logger
        "scitex.errors": {
            "handlers": ["error_file", "console"],
            "level": "ERROR",
            "propagate": False,
        },
        # Git operations
        "scitex.git": {
            "handlers": ["git_file", "console_file"],
            "level": "INFO",
            "propagate": False,
        },
        # LaTeX compilation
        "scitex.compilation": {
            "handlers": ["compilation_file", "console_file"],
            "level": "INFO",
            "propagate": False,
        },
        # Django's built-in loggers
        "django": {
            "handlers": ["console"],
            "level": "INFO",
        },
        "django.request": {
            "handlers": ["error_file"],
            "level": "ERROR",
            "propagate": False,
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
}
