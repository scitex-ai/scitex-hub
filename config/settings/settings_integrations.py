#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Timestamp: 2026-02-04
# File: config/settings/settings_integrations.py
"""Third-party integrations settings for SciTeX Cloud."""

import os
from pathlib import Path

# Get BASE_DIR from parent
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# ---------------------------------------
# SciTeX Scholar Search Settings
# ---------------------------------------
# Enable/disable search pipeline caching
SCITEX_SCHOLAR_USE_CACHE = os.getenv("SCITEX_SCHOLAR_USE_CACHE", "True").lower() in [
    "true",
    "1",
    "yes",
]

# Maximum parallel workers for parallel search pipeline
SCITEX_SCHOLAR_MAX_WORKERS = int(os.getenv("SCITEX_SCHOLAR_MAX_WORKERS", "5"))

# Timeout per engine in seconds
SCITEX_SCHOLAR_TIMEOUT_PER_ENGINE = int(
    os.getenv("SCITEX_SCHOLAR_TIMEOUT_PER_ENGINE", "60")
)

# Preferred engines (comma-separated)
SCITEX_SCHOLAR_ENGINES = os.getenv(
    "SCITEX_SCHOLAR_ENGINES", "CrossRef,PubMed,Semantic_Scholar,arXiv,OpenAlex"
).split(",")

# Default search mode: "parallel" or "single"
SCITEX_SCHOLAR_DEFAULT_MODE = os.getenv("SCITEX_SCHOLAR_DEFAULT_MODE", "parallel")

# Public API campaign key (shared key for experiments/demos)
# Set via environment: SCITEX_CLOUD_CAMPAIGN_API_KEY=your-shared-key
SCITEX_CLOUD_CAMPAIGN_API_KEY = os.getenv("SCITEX_CLOUD_CAMPAIGN_API_KEY", None)

# ---------------------------------------
# SciTeX Writer Settings
# ---------------------------------------
# Check common locations for scitex-writer template
_WRITER_TEMPLATE_LOCATIONS = [
    Path(os.getenv("SCITEX_WRITER_TEMPLATE_PATH", "")),
    Path.home() / "proj" / "scitex-writer",
    Path("/tmp/scitex-writer"),
    BASE_DIR / "docs" / "scitex_writer_template",
]

SCITEX_WRITER_TEMPLATE_PATH = None
for location in _WRITER_TEMPLATE_LOCATIONS:
    if location and location.exists():
        SCITEX_WRITER_TEMPLATE_PATH = location
        break

# ---------------------------------------
# CrossRef Local API
# ---------------------------------------
CROSSREF_INTERNAL_URL = os.getenv("CROSSREF_INTERNAL_URL", "http://crossref:31291")

# CrossRef database path for citation graph service
CROSSREF_DB_PATH = os.getenv(
    "CROSSREF_DB_PATH", str(Path.home() / "proj/crossref_local/data/crossref.db")
)

# ---------------------------------------
# REST Framework
# ---------------------------------------
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
        "rest_framework.renderers.BrowsableAPIRenderer",
    ],
}

# EOF
