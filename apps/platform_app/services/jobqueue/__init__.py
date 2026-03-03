# -*- coding: utf-8 -*-
# Timestamp: 2026-03-04
# Author: ywatanabe
# File: apps/platform_app/services/jobqueue/__init__.py

"""
JobQueue service — public API.

Usage
-----
from apps.platform_app.services.jobqueue import jobqueue, update_progress

job = jobqueue.submit("my_app", "process_data", project, owner, params={})
update_progress(str(job.id), 50, "halfway done")
info = jobqueue.status(str(job.id))
"""

from apps.platform_app.services.jobqueue.executor import JobQueue, jobqueue
from apps.platform_app.services.jobqueue.progress import update_progress

__all__ = [
    "JobQueue",
    "jobqueue",
    "update_progress",
]

# EOF
