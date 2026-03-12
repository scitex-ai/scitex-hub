"""JobQueue client — background job submission and monitoring.

REST endpoints:
  POST  /platform/api/jobs/<app>/submit/           (submit)
  GET   /platform/api/jobs/<app>/<job_id>/          (status)
  POST  /platform/api/jobs/<app>/<job_id>/cancel/   (cancel)
  GET   /platform/api/jobs/<app>/                   (list)
"""

from __future__ import annotations

from typing import Any, Optional

from ._client import get_client


def submit(
    app: str,
    job_name: str,
    *,
    params: Optional[dict] = None,
    project_id: Optional[str] = None,
) -> dict:
    """Submit a background job."""
    client = get_client()
    data: dict[str, Any] = {"job_name": job_name}
    if params:
        data["params"] = params
    if project_id:
        data["project_id"] = project_id
    return client.request("POST", f"/platform/api/jobs/{app}/submit/", data=data)


def status(app: str, job_id: str) -> dict:
    """Get job status and result."""
    client = get_client()
    return client.request("GET", f"/platform/api/jobs/{app}/{job_id}/")


def cancel(app: str, job_id: str) -> dict:
    """Cancel a running job."""
    client = get_client()
    return client.request("POST", f"/platform/api/jobs/{app}/{job_id}/cancel/")


def list_jobs(app: str) -> dict:
    """List all jobs for an app."""
    client = get_client()
    return client.request("GET", f"/platform/api/jobs/{app}/")


# EOF
