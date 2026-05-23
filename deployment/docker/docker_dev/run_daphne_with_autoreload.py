#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Timestamp: "2025-11-20 15:59:01 (ywatanabe)"
# File: /home/ywatanabe/proj/scitex-hub/deployment/docker/docker_dev/run_daphne_with_autoreload.py


"""
Run Daphne with Django's autoreload mechanism.

This enables django-browser-reload to work properly by using Django's
autoreload system to detect file changes and send events to the browser.

Uses WatchFilesReloader for better Docker volume change detection.
"""
import os
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(project_root))

# Set Django settings module
os.environ.setdefault(
    "DJANGO_SETTINGS_MODULE",
    os.getenv("SCITEX_CLOUD_DJANGO_SETTINGS_MODULE", "config.settings.settings_dev"),
)

# Import Django's autoreload before setup
from django.utils import autoreload

# Note: Template hot reload is handled by Django's autoreload + django-browser-reload
# Visitor pool initialization is optimized with fast-path check for instant restarts

# Now setup Django
import django

django.setup()


def run_daphne():
    """Run Daphne ASGI server using exec to replace the process."""
    print("🔥 Starting Daphne with hot reload...")
    print("   Template changes: django-browser-reload → browser refresh")
    print("   Python changes: Django autoreload → server restart (fast)")
    print("   TypeScript watch: .ts → .js compilation")

    # Use os.execvp to replace the current process with Daphne
    # This ensures proper cleanup when autoreload kills the process
    import os

    os.execvp(
        "daphne",
        [
            "daphne",
            "-b",
            "0.0.0.0",
            "-p",
            "8000",
            "config.asgi:application",
        ],
    )


if __name__ == "__main__":
    # Run Daphne with Django's autoreload wrapper
    # This allows django-browser-reload to detect changes and send events
    autoreload.run_with_reloader(run_daphne)

# EOF
