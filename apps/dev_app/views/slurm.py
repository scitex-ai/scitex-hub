"""SLURM management views for development."""

import logging
import subprocess

from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.http import require_POST

logger = logging.getLogger(__name__)


@require_POST
def cancel_all_jobs_api(request):
    """Cancel all SLURM jobs (dev only)."""
    if not settings.DEBUG:
        return JsonResponse({"error": "Only available in DEBUG mode"}, status=403)

    if not request.user.is_staff:
        return JsonResponse({"error": "Staff only"}, status=403)

    try:
        # Get list of all jobs first
        queue = subprocess.run(
            ["squeue", "--noheader", "-o", "%i"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        job_ids = queue.stdout.strip().split("\n") if queue.stdout.strip() else []
        job_count = len(job_ids)

        if job_count == 0:
            return JsonResponse({"message": "No jobs to cancel", "cancelled": 0})

        result = subprocess.run(
            ["scancel"] + job_ids,
            capture_output=True,
            text=True,
            timeout=30,
        )

        # scancel may report "Socket timed out" but still succeed
        if result.returncode != 0:
            error_msg = result.stderr.strip() or result.stdout.strip()
            if "Socket timed out" in error_msg:
                logger.warning("scancel reported timeout but jobs likely cancelled")
            else:
                return JsonResponse(
                    {"message": f"Cancel failed: {error_msg}"},
                    status=500,
                )
    except FileNotFoundError:
        return JsonResponse(
            {"message": "scancel not found — SLURM not installed"},
            status=500,
        )
    except Exception as e:
        return JsonResponse(
            {"message": f"Cancel error: {e}"},
            status=500,
        )

    return JsonResponse(
        {
            "message": f"Cancelled {job_count} job(s)",
            "cancelled": job_count,
        }
    )


# EOF
