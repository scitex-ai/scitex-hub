# -*- coding: utf-8 -*-
# Timestamp: 2025-11-25
# Author: ywatanabe
# File: config/celery.py

"""
Celery configuration for SciTeX Hub.

Provides async task processing with fair scheduling and rate limiting.
"""

import os

from celery import Celery

# Set default Django settings module
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.settings_dev")

# Create Celery app
app = Celery("scitex_hub")

# Configure from Django settings with CELERY_ prefix
app.config_from_object("django.conf:settings", namespace="CELERY")

# Auto-discover tasks in all Django apps
app.autodiscover_tasks()

# Close DB connections at TASK boundaries. Imported for its signal handlers:
# a Celery task is not an HTTP request, so CONN_MAX_AGE/close_old_connections is
# never applied to it, and the threads pool then accumulates one PostgreSQL
# backend per worker thread. See config/celery_db_lifecycle.py and issue #777.
from config import celery_db_lifecycle as _celery_db_lifecycle  # noqa: E402,F401


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    """Debug task to verify Celery is working."""
    print(f"Request: {self.request!r}")


# EOF
