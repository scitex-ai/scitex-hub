#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Shared fixtures for the docs_app tests."""

import subprocess
import sys
from pathlib import Path

import pytest
from django.utils import translation

PROJECT_ROOT = Path(__file__).resolve().parents[3]


@pytest.fixture
def compiled_catalogs():
    """Compile locale/**/*.po -> .mo so a ja render reads the real catalog."""
    script = PROJECT_ROOT / "scripts" / "i18n" / "compile_catalogs.py"
    result = subprocess.run(
        [sys.executable, str(script)], cwd=PROJECT_ROOT, capture_output=True, text=True
    )
    assert result.returncode == 0, result.stdout + result.stderr
    translation.trans_real._translations.clear()
    yield
