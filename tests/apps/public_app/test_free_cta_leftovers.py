#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""No "free" signup CTAs outlive #813's card-required rule.

Card hub-card-required-copy-leftovers-20260914: features.html, products/hub.html,
release_note.html, the premium_subscription view, and the console templates
still said "Get Started Free" / "Start Free Trial" / "Sign up free".
They now reuse #813's "Start your 30-day trial".
"""

import re
import subprocess
import sys
from pathlib import Path

import pytest
from django.urls import reverse
from django.utils import translation

PROJECT_ROOT = Path(__file__).resolve().parents[3]

RETIRED_CTAS = ("get started free", "start free trial", "sign up free")

LEFTOVER_SOURCES = (
    "apps/infra/public_app/templates/public_app/features.html",
    "apps/infra/public_app/templates/public_app/products/hub.html",
    "apps/infra/public_app/templates/public_app/release_note.html",
    "apps/infra/public_app/views/landing.py",
    "apps/workspace/console_app/templates/console_app/workspace.html",
    "apps/workspace/console_app/templates/console_app/console_partial.html",
)


@pytest.mark.parametrize("relpath", LEFTOVER_SOURCES)
def test_source_has_no_free_signup_cta(relpath):
    # Arrange
    text = (PROJECT_ROOT / relpath).read_text(encoding="utf-8").lower()
    # Act
    found = [cta for cta in RETIRED_CTAS if cta in text]
    # Assert
    assert found == []


@pytest.fixture
def compiled_catalogs():
    script = PROJECT_ROOT / "scripts" / "i18n" / "compile_catalogs.py"
    result = subprocess.run(
        [sys.executable, str(script)], cwd=PROJECT_ROOT, capture_output=True, text=True
    )
    assert result.returncode == 0, result.stderr
    translation.trans_real._translations.clear()


@pytest.mark.django_db
def test_japanese_releases_page_shows_the_translated_trial_cta(client, compiled_catalogs):
    # Arrange
    cookie = {"HTTP_COOKIE": "django_language=ja"}
    # Act
    html = client.get(reverse("public_app:releases"), **cookie).content.decode()
    # Assert
    assert re.search(r">\s*30日間のトライアルを開始\s*</a>", html)
