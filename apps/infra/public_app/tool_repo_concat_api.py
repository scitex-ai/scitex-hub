#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Repository Concatenator Tool - API Endpoints

Handles cloning Git repositories and concatenating files.

Re-exports from specialized submodules:
- tool_repo_utils: URL parsing and SSH key handling
- tool_repo_clone: Clone and analyze API endpoint
- tool_repo_concat: Concatenate API endpoint
"""

from __future__ import annotations

from .tool_repo_clone import api_clone_and_analyze, get_temp_repos
from .tool_repo_concat import api_concatenate_repo
from .tool_repo_utils import (
    _convert_https_to_ssh,
    _get_user_ssh_key,
    parse_github_url,
)

__all__ = [
    # API endpoints
    "api_clone_and_analyze",
    "api_concatenate_repo",
    # Utilities
    "parse_github_url",
    "_get_user_ssh_key",
    "_convert_https_to_ssh",
    "get_temp_repos",
]


# EOF
