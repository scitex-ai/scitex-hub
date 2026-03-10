#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""App Maker — validation and utility helpers."""

from __future__ import annotations

import re

_FORBIDDEN_PATTERNS = [
    r"\bos\.system\b",
    r"\bsubprocess\b",
    r"\b__import__\b",
    r"\beval\s*\(",
    r"\bexec\s*\(",
    r"\bopen\s*\(",
    r"\bshutil\b",
]


def has_forbidden_patterns(source: str) -> bool:
    """Check if source code contains potentially dangerous patterns."""
    for pattern in _FORBIDDEN_PATTERNS:
        if re.search(pattern, source):
            return True
    return False


# EOF
