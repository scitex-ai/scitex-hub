"""SLURM management views for development."""

import logging
import subprocess

from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.http import require_POST

logger = logging.getLogger(__name__)


@require_POST
def restart_slurm_api(request):
    """Restart SLURM services (dev only)."""
    if not settings.DEBUG:
        return JsonResponse({"error": "Only available in DEBUG mode"}, status=403)

    if not request.user.is_staff:
        return JsonResponse({"error": "Staff only"}, status=403)

    errors = []
    for service in ["slurmctld", "slurmd"]:
        try:
            subprocess.run(
                ["sudo", "service", service, "restart"],
                capture_output=True,
                text=True,
                timeout=15,
            )
        except Exception as e:
            errors.append(f"{service}: {e}")

    if errors:
        return JsonResponse(
            {"message": f"Partial restart. Errors: {'; '.join(errors)}"},
            status=207,
        )
    return JsonResponse({"message": "SLURM services restarted successfully"})


# EOF
