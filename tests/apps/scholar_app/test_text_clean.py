#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Unit tests for scholar text_clean (JATS/entity stripping). Pure, no DB."""
from apps.workspace.scholar_app.views.search.text_clean import (
    clean_snippet,
    clean_text,
)


def test_strips_jats_tags():
    assert clean_text("<jats:p>Hello world</jats:p>") == "Hello world"


def test_strips_inline_tags_with_space():
    # Adjacent tagged spans must not jam words together ("AbstractThe").
    assert clean_text("<jats:title>Abstract</jats:title><jats:p>The hippo</jats:p>") == "Abstract The hippo"


def test_unescapes_entities():
    assert clean_text("Learning &amp; Memory") == "Learning & Memory"


def test_scp_title():
    assert clean_text("<scp>DREADD</scp>-inactivation of CA1") == "DREADD -inactivation of CA1"


def test_empty_and_none():
    assert clean_text("") == ""
    assert clean_text(None) == ""
    assert clean_snippet("") == "No abstract available...."


def test_snippet_truncates():
    out = clean_snippet("x" * 300)
    assert out.endswith("...") and len(out) == 203


def test_snippet_short_passthrough():
    assert clean_snippet("Short abstract.") == "Short abstract."
