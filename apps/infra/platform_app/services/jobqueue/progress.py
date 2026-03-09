# -*- coding: utf-8 -*-
# Timestamp: 2026-03-04
# Author: ywatanabe
# File: apps/platform_app/services/jobqueue/progress.py

"""
Progress updater for PlatformJob records.

Updates the job's progress_percent and progress_message in the database
and optionally broadcasts a progress event via Django Channels.
"""

import logging  # noqa: STX-I007 — Django context, no @stx.session

logger = logging.getLogger("scitex")


def update_progress(job_id: str, percent: int, message: str = "") -> bool:
    """
    Update the progress of a PlatformJob and optionally broadcast via Channels.

    Parameters
    ----------
    job_id : str
        UUID of the PlatformJob to update.
    percent : int
        Progress percentage (0-100). Clamped to valid range.
    message : str
        Human-readable progress message (optional).

    Returns
    -------
    bool
        True if the job was found and updated, False otherwise.
    """
    from apps.infra.platform_app.models import PlatformJob

    percent = max(0, min(100, percent))

    updated = PlatformJob.objects.filter(pk=job_id).update(
        progress_percent=percent,
        progress_message=message,
    )
    if not updated:
        logger.warning("update_progress: PlatformJob %s not found", job_id)
        return False

    _broadcast_progress(job_id, percent, message)
    return True


def _broadcast_progress(job_id: str, percent: int, message: str) -> None:
    """
    Send a progress event to the job's Channels group if available.

    Uses the channel layer from Django Channels asynchronously via
    async_to_sync. Silently skips if Channels is not configured.
    """
    try:
        from asgiref.sync import async_to_sync
        from channels.layers import get_channel_layer

        layer = get_channel_layer()
        if layer is None:
            return

        group_name = _job_group_name(job_id)
        async_to_sync(layer.group_send)(
            group_name,
            {
                "type": "job.progress",
                "job_id": job_id,
                "percent": percent,
                "message": message,
            },
        )
    except Exception as exc:
        # Channels broadcast is best-effort — never raise from here.
        logger.debug("Progress broadcast skipped for %s: %s", job_id, exc)


def _job_group_name(job_id: str) -> str:
    """Return the Channels group name for a given job ID."""
    safe_id = str(job_id).replace("-", "_")
    return f"job_{safe_id}"


# EOF
