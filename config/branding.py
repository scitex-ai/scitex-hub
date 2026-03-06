#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SciTeX Cloud Branding Constants - Single Source of Truth

All site-wide branding text should be defined here and referenced
via Django settings or context processors.
"""

# Core branding
SITE_NAME = "SciTeX"
SITE_TAGLINE = "Research Automation for AI and Humans"
SITE_DESCRIPTION = (
    "Python toolkit + MCP server for literature search, "
    "statistics, visualization, and manuscript writing."
)

# Meta descriptions for SEO
META_DESCRIPTION_DEFAULT = f"{SITE_NAME} - {SITE_TAGLINE}"
META_DESCRIPTION_LONG = (
    f"{SITE_NAME}: {SITE_TAGLINE}. "
    "An integrated ecosystem of tools from hypothesis to publication."
)

# Social media / Open Graph
OG_TITLE = f"{SITE_NAME} - {SITE_TAGLINE}"
OG_DESCRIPTION = META_DESCRIPTION_LONG
