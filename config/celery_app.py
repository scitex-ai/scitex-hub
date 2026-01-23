# -*- coding: utf-8 -*-
# Timestamp: 2025-11-25
# Author: ywatanabe
# File: config/celery.py

"""
Celery configuration for SciTeX Cloud.

Provides async task processing with fair scheduling and rate limiting.
"""

import os
from celery import Celery

# Set default Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.settings_dev')

# Create Celery app
app = Celery('scitex_cloud')

# Configure from Django settings with CELERY_ prefix
app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-discover tasks in all Django apps
app.autodiscover_tasks()


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    """Debug task to verify Celery is working."""
    print(f'Request: {self.request!r}')


# EOF
