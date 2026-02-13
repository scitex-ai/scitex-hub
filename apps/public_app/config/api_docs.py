#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Timestamp: "2025-02-05 (ywatanabe)"
# File: /home/ywatanabe/proj/scitex-cloud/apps/public_app/config/api_docs.py
# ----------------------------------------
from __future__ import annotations

"""
API Documentation Configuration

Centralized configuration for API documentation sections.
This enables programmatic testing and consistent navigation.
"""

# API Documentation Sections
# Each section has:
#   - emoji: Section emoji (separate for proper rendering)
#   - text: Section title text
#   - title: Full display title (emoji + text)
#   - template: Path to the template partial
#   - subsections: List of subsections with id, title, and emoji
API_DOC_SECTIONS = {
    "getting-started": {
        "emoji": "🚀",
        "text": "Getting Started",
        "title": "🚀 Getting Started",
        "template": "public_app/pages/api-docs-partials/getting-started.html",
        "subsections": [
            {"id": "introduction", "title": "Introduction", "emoji": "📖"},
            {"id": "authentication", "title": "Authentication", "emoji": "🔐"},
            {"id": "quickstart", "title": "Quick Start", "emoji": "⚡"},
            {"id": "errors", "title": "Error Handling", "emoji": "⚠️"},
            {"id": "rate-limits", "title": "Rate Limits", "emoji": "🚦"},
        ],
    },
    "public-api": {
        "emoji": "🌐",
        "text": "Public API",
        "title": "🌐 Public API",
        "template": "public_app/pages/api-docs-partials/public-api.html",
        "badge": "New",
        "subsections": [
            {"id": "public-search", "title": "Public Search", "emoji": "🔍"},
            {"id": "public-info", "title": "API Info", "emoji": "ℹ️"},
        ],
    },
    "scholar-api": {
        "emoji": "📚",
        "text": "Scholar API",
        "title": "📚 Scholar API",
        "template": "public_app/pages/api-docs-partials/scholar-api.html",
        "subsections": [
            {"id": "scholar-search", "title": "Search Papers", "emoji": "🔍"},
            {"id": "scholar-databases", "title": "Database Search", "emoji": "🗄️"},
            {"id": "scholar-bibtex", "title": "BibTeX Enrichment", "emoji": "📝"},
            {"id": "scholar-export", "title": "Export Citations", "emoji": "📤"},
            {"id": "scholar-library", "title": "Library Management", "emoji": "📖"},
        ],
    },
    "stats-api": {
        "emoji": "📊",
        "text": "Stats API",
        "title": "📊 Stats API",
        "template": "public_app/pages/api-docs-partials/stats-api.html",
        "badge": "New",
        "subsections": [
            {"id": "stats-calculate", "title": "Run Tests", "emoji": "🧪"},
            {"id": "stats-describe", "title": "Descriptive", "emoji": "📈"},
            {"id": "stats-recommend", "title": "Recommendations", "emoji": "💡"},
            {"id": "stats-effect-size", "title": "Effect Size", "emoji": "📏"},
            {"id": "stats-posthoc", "title": "Post-hoc", "emoji": "🔗"},
            {"id": "stats-power", "title": "Power Analysis", "emoji": "⚡"},
            {"id": "stats-correct", "title": "Corrections", "emoji": "✅"},
            {"id": "stats-flowchart", "title": "Flowchart", "emoji": "🗺️"},
        ],
    },
    "writer-api": {
        "emoji": "✍️",
        "text": "Writer API",
        "title": "✍️ Writer API",
        "template": "public_app/pages/api-docs-partials/writer-api.html",
        "subsections": [
            {"id": "writer-sections", "title": "Sections", "emoji": "📑"},
            {"id": "writer-compile", "title": "Compilation", "emoji": "⚙️"},
            {"id": "writer-git", "title": "Version Control", "emoji": "📌"},
        ],
    },
    "project-api": {
        "emoji": "📁",
        "text": "Project API",
        "title": "📁 Project API",
        "template": "public_app/pages/api-docs-partials/project-api.html",
        "subsections": [
            {"id": "project-files", "title": "File Operations", "emoji": "📄"},
            {"id": "project-git", "title": "Git Operations", "emoji": "🔀"},
        ],
    },
    "resources": {
        "emoji": "📦",
        "text": "Resources",
        "title": "📦 Resources",
        "template": "public_app/pages/api-docs-partials/resources.html",
        "subsections": [
            {"id": "sdks", "title": "SDKs & Libraries", "emoji": "🛠️"},
            {"id": "webhooks", "title": "Webhooks", "emoji": "🔔"},
            {"id": "changelog", "title": "Changelog", "emoji": "📋"},
        ],
    },
}

# Order of sections in navigation
API_DOC_SECTION_ORDER = [
    "getting-started",
    "public-api",
    "scholar-api",
    "stats-api",
    "writer-api",
    "project-api",
    "resources",
]

# Default section (landing page)
API_DOC_DEFAULT_SECTION = "getting-started"


def get_section(section_key: str) -> dict | None:
    """Get a section by its key."""
    return API_DOC_SECTIONS.get(section_key)


def get_all_sections() -> list[dict]:
    """Get all sections in order."""
    return [{"key": key, **API_DOC_SECTIONS[key]} for key in API_DOC_SECTION_ORDER]


def get_all_subsection_ids() -> list[str]:
    """Get all subsection IDs for testing anchor links."""
    ids = []
    for section in API_DOC_SECTIONS.values():
        for subsection in section.get("subsections", []):
            ids.append(subsection["id"])
    return ids


# ============================================================
# Campaign Token Utilities
# ============================================================
# Format: scitex-cloud-campaign-YYYYMMDD-YYYYMMDD-HASHTAG
# Example: scitex-cloud-campaign-20250201-20250228-alpha
import re
from datetime import datetime

CAMPAIGN_TOKEN_PATTERN = re.compile(
    r"^scitex-cloud-campaign-(\d{8})-(\d{8})-([a-z0-9_-]+)$"
)


def generate_campaign_token(
    start_date: datetime,
    end_date: datetime,
    hashtag: str,
) -> str:
    """Generate a standardized campaign token.

    Format: scitex-cloud-campaign-YYYYMMDD-YYYYMMDD-hashtag

    Args:
        start_date: Campaign start date
        end_date: Campaign end date
        hashtag: Campaign identifier (lowercase alphanumeric, hyphens, underscores)

    Returns:
        Formatted campaign token string
    """
    hashtag_clean = re.sub(r"[^a-z0-9_-]", "", hashtag.lower())
    return (
        f"scitex-cloud-campaign-"
        f"{start_date.strftime('%Y%m%d')}-"
        f"{end_date.strftime('%Y%m%d')}-"
        f"{hashtag_clean}"
    )


def parse_campaign_token(token: str) -> dict | None:
    """Parse a campaign token into its components.

    Args:
        token: Campaign token string

    Returns:
        Dict with start_date, end_date, hashtag, or None if invalid
    """
    match = CAMPAIGN_TOKEN_PATTERN.match(token)
    if not match:
        return None

    start_str, end_str, hashtag = match.groups()
    try:
        start_date = datetime.strptime(start_str, "%Y%m%d")
        end_date = datetime.strptime(end_str, "%Y%m%d")
        return {
            "start_date": start_date,
            "end_date": end_date,
            "hashtag": hashtag,
            "is_active": start_date <= datetime.now() <= end_date,
        }
    except ValueError:
        return None


def is_valid_campaign_token(token: str) -> bool:
    """Check if a token matches the campaign token format."""
    return bool(CAMPAIGN_TOKEN_PATTERN.match(token))


# Active campaign tokens for API docs examples
CAMPAIGN_TOKENS = {
    "alpha": {
        "token": "scitex-cloud-campaign-20260101-20261231-alpha",
        "description": "Alpha testing campaign",
        "permissions": ["read", "search"],
    },
}


def get_active_campaign_token() -> str | None:
    """Get the currently active campaign token for API examples."""
    now = datetime.now()
    for info in CAMPAIGN_TOKENS.values():
        parsed = parse_campaign_token(info["token"])
        if parsed and parsed["is_active"]:
            return info["token"]
    return None


# EOF
