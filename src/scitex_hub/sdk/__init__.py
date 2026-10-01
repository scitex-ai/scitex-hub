"""Backward-compatible Hub names for the consolidated SciTeX SDK client.

Shared client code lives in scitex_sdk.app.sdk.
This module re-exports for backward compatibility.

Usage (preferred):
    >>> from scitex_sdk.app.sdk import data, files, jobs, scitex, external

Usage (legacy, still works):
    >>> from scitex_hub.sdk import data, files, jobs, scitex, external
"""

from __future__ import annotations

import importlib
import sys

from scitex_sdk.app.sdk import _cloud_data as data  # noqa: F401
from scitex_sdk.app.sdk import _cloud_external as external  # noqa: F401
from scitex_sdk.app.sdk import _cloud_files as files  # noqa: F401
from scitex_sdk.app.sdk import _cloud_jobs as jobs  # noqa: F401
from scitex_sdk.app.sdk import _cloud_scitex as scitex  # noqa: F401
from scitex_sdk.app.sdk._client import (
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

# ── Backward-compatible module aliases ────────────────────────────────
# Register old private module names in sys.modules so that direct imports
# like ``from scitex_hub.sdk._client import PlatformClient`` continue
# to work.  They resolve to the canonical scitex_sdk.app.sdk modules.
_COMPAT_MODULES = {
    "_data": "scitex_sdk.app.sdk._cloud_data",
    "_files": "scitex_sdk.app.sdk._cloud_files",
    "_jobs": "scitex_sdk.app.sdk._cloud_jobs",
    "_client": "scitex_sdk.app.sdk._client",
    "_external": "scitex_sdk.app.sdk._cloud_external",
    "_scitex": "scitex_sdk.app.sdk._cloud_scitex",
}

for _alias, _target in _COMPAT_MODULES.items():
    sys.modules[f"{__name__}.{_alias}"] = importlib.import_module(_target)

del _alias, _target

# EOF
