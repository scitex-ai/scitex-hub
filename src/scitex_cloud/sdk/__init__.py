"""SciTeX SDK — community app development kit for SciTeX Cloud.

Wraps Platform REST APIs (DataStore, FileVault, JobQueue, SciTeX Bridge, External API)
into a clean Python interface. Works from anywhere: Apptainer containers, CLI, local dev.

Auth via SCITEX_API_TOKEN + SCITEX_API_URL env vars.

Usage:
    >>> from scitex_cloud.sdk import data, files, jobs, scitex, external
    >>> data.create("my-app", "Experiment", {"title": "Test"})
    >>> files.upload("my-app", "out.csv", csv_content)
    >>> jobs.submit("my-app", "export_csv", params={"fmt": "xlsx"})
"""

from . import _data as data
from . import _external as external
from . import _files as files
from . import _jobs as jobs
from . import _scitex as scitex
from ._client import PlatformClient, get_client, reset_client

__all__ = [
    "data",
    "files",
    "jobs",
    "scitex",
    "external",
    "PlatformClient",
    "get_client",
    "reset_client",
]

# EOF
