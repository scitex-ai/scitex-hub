"""SciTeX SDK — backward-compatible re-export from scitex-app.

All SDK code now lives in the standalone scitex-app package.
This module re-exports for backward compatibility.

Usage (preferred):
    >>> from scitex_app.sdk import data, files, jobs, scitex, external

Usage (legacy, still works):
    >>> from scitex_cloud.sdk import data, files, jobs, scitex, external
"""

from scitex_app.sdk import _cloud_data as data  # noqa: F401
from scitex_app.sdk import _cloud_external as external  # noqa: F401
from scitex_app.sdk import _cloud_files as files  # noqa: F401
from scitex_app.sdk import _cloud_jobs as jobs  # noqa: F401
from scitex_app.sdk import _cloud_scitex as scitex  # noqa: F401
from scitex_app.sdk._client import (
    PlatformClient,  # noqa: F401
    get_client,  # noqa: F401
    reset_client,  # noqa: F401
)

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
