#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Timestamp: "2026-02-18 20:15:00 (ywatanabe)"
# File: /home/ywatanabe/proj/scitex-hub/scripts/demo/_config.py


"""Configuration for SciTeX demo screenshot capture."""

import os
from collections import OrderedDict
from pathlib import Path

from dotenv import load_dotenv
from scitex.logging import getLogger

logger = getLogger(__name__)

# Load environment variables from .env file
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
ENV_FILE = PROJECT_ROOT / "deployment" / "docker" / "envs" / ".env.dev"

if ENV_FILE.exists():
    load_dotenv(ENV_FILE)
    logger.info(f"Loaded environment from {ENV_FILE}")
else:
    logger.warning(f"Environment file not found: {ENV_FILE}")

BASE_URL = "http://127.0.0.1:8000"

# Load test user credentials from environment variables
TEST_USER = os.getenv("SCITEX_HUB_TEST_USER_USERNAME", "test-user")
TEST_PASSWORD = os.getenv("SCITEX_HUB_TEST_USER_PASSWORD", "Password123!")

# Standard viewport sizes for consistent screenshots
VIEWPORT_PRESETS = {
    "desktop": {"width": 1920, "height": 1080},
    "laptop": {"width": 1366, "height": 768},
    "tablet": {"width": 768, "height": 1024},
    "mobile": {"width": 375, "height": 667},
}

# Default preset for screenshots
DEFAULT_VIEWPORT = "desktop"

# ── Page groups ──────────────────────────────────────────────────────
# Module pages: all workspace apps under /apps/ prefix
MODULE_PAGES = [
    # Writer panels
    "/apps/writer/#pdf",
    "/apps/writer/#citations",
    "/apps/writer/#figures",
    "/apps/writer/#tables",
    "/apps/writer/#history",
    "/apps/writer/#collaboration",
    # Scholar tabs
    "/apps/scholar/#library",
    "/apps/scholar/#search",
    "/apps/scholar/#bibtex",
    "/apps/scholar/#graph",
    # Other workspace modules
    "/apps/figrecipe/",
    "/apps/console/",
    "/apps/clew/",
    "/apps/home/",
    "/apps/discovery/",
    "/apps/figrecipe/",
    "/apps/store/",
    "/apps/tools/",
]

# All page groups (ordered for deterministic numbering)
PAGE_GROUPS = OrderedDict(
    [
        (
            "repo",
            [
                f"/{TEST_USER}/",
                f"/{TEST_USER}/default-project/",
            ],
        ),
        ("modules", MODULE_PAGES),
        (
            "tools",
            [
                "/apps/tools/render-md/",
                "/apps/tools/diff-texts/",
                "/apps/tools/format-json/",
                "/apps/tools/convert-docx-to-latex/",
                "/apps/tools/render-mmd/",
                "/apps/tools/view-image/",
                "/apps/tools/resize-image/",
                "/apps/tools/crop-images/",
                "/apps/tools/convert-image-format/",
                "/apps/tools/concat-images/",
                "/apps/tools/convert-images-to-gif/",
                "/apps/tools/convert-images-to-pdf/",
                "/apps/tools/convert-pdf-to-images/",
                "/apps/tools/merge-pdf/",
                "/apps/tools/compress-pdf/",
                "/apps/tools/split-pdf/",
                "/apps/tools/edit-video/",
                "/apps/tools/view-plot/",
                "/apps/tools/test-scitex-plot/",
                "/apps/tools/pick-color/",
                "/apps/tools/inspect-html-element/",
                "/apps/tools/concat-repo/",
                "/apps/tools/generate-qr/",
                "/apps/tools/run-stats/",
                "/apps/tools/scrape-citations/",
            ],
        ),
        (
            "docs",
            [
                "/apps/docs/",
                "/apps/docs/python/",
                "/apps/docs/api/",
                "/apps/docs/content/python-packages/",
                "/apps/docs/content/mcp-tools-local/",
                "/apps/docs/content/mcp-tools-https/",
                "/apps/docs/content/ssh-access/",
                "/apps/docs/content/console/",
                "/apps/docs/content/chat/",
                "/apps/docs/content/agent/",
                "/apps/docs/content/agent-tooling/",
                "/apps/docs/content/auto-response/",
                "/apps/docs/content/app-maker/",
                "/apps/docs/content/app-maker-users/",
                "/apps/docs/content/app-maker-creators/",
                "/apps/docs/content/app-maker-admins/",
                "/apps/docs/content/web-api/",
                "/apps/docs/content/design-rules/",
                "/apps/docs/content/shared-ts-components/",
                "/apps/docs/content/shared-ts-utilities/",
                "/apps/docs/content/shared-css-system/",
                "/apps/docs/content/visitor-lifecycle/",
                "/apps/docs/content/self-hosting/",
                "/apps/docs/content/agpl-v3/",
            ],
        ),
        (
            "basic",
            [
                "/",
                "/about/",
                "/server-status/",
                "/demos/",
            ],
        ),
    ]
)

# Groups where #default/#zen hash mode applies
ZEN_GROUPS = {"modules"}

# Groups needing longer wait (SPA apps with dynamic content)
SLOW_GROUPS = {"modules"}

VALID_GROUPS = list(PAGE_GROUPS.keys())


def format_groups_help() -> str:
    """Build page-group listing for --help display."""
    lines = []
    for name, pages in PAGE_GROUPS.items():
        lines.append(f"    {name:10s}: {', '.join(pages)}")
    return "\n".join(lines)


def build_pages(groups: str = "repo,modules", zen: bool = True):
    """
    Build page list and slow-page set from selected groups.

    Args:
        groups: Comma-separated group names, or "all".
                Prefix a group with "-" to exclude it.
                Examples:
                  "all,-tools"          → everything except tools
                  "all,-tools,-docs"    → everything except tools and docs
                  "modules,repo"        → only modules and repo
                  "all,-basic"          → all except basic
        zen: Include zen mode for applicable groups

    Returns:
        Tuple of (pages_list, slow_pages_set)
    """
    tokens = [g.strip() for g in groups.split(",")]

    includes = [t for t in tokens if not t.startswith("-")]
    excludes = {t.lstrip("-") for t in tokens if t.startswith("-")}

    if not includes or includes == ["all"]:
        selected = list(VALID_GROUPS)
    else:
        selected = includes

    selected = [g for g in selected if g not in excludes]

    # Validate
    for g in selected + list(excludes):
        if g not in VALID_GROUPS:
            logger.warning(f"Unknown page group: '{g}' (valid: {VALID_GROUPS})")

    pages = []
    slow_pages = set()

    for group_name in selected:
        if group_name not in PAGE_GROUPS:
            logger.warning(
                f"Unknown page group: '{group_name}' (valid: {VALID_GROUPS})"
            )
            continue

        group_pages = PAGE_GROUPS[group_name]
        is_zen_group = group_name in ZEN_GROUPS
        is_slow_group = group_name in SLOW_GROUPS

        if is_zen_group:
            for p in group_pages:
                default_page = f"{p}#default"
                pages.append(default_page)
                slow_pages.add(default_page)
                if zen:
                    zen_page = f"{p}#zen"
                    pages.append(zen_page)
                    slow_pages.add(zen_page)
        else:
            for p in group_pages:
                pages.append(p)
                if is_slow_group:
                    slow_pages.add(p)

    return pages, slow_pages


# EOF
