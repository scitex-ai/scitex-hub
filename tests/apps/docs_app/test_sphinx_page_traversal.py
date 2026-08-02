#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Regression tests for the docs `?page=` path-traversal defect.

Card: sec-docs-sphinx-page-traversal-latent-20260802

`docs_app.views.docs_content` has no ``@login_required``, so ``?page=`` is
attacker-controlled AND unauthenticated. It used to be joined straight onto the
Sphinx docs directory with no containment, and `extract_sphinx_body` returned the
whole file when the content was not recognisably Sphinx HTML — together, an
unauthenticated arbitrary-file read.

It was inert when found ONLY because zero packages were registered, so no
``pkg-*`` slug existed to reach the branch. That is a config accident, not a fix:
publishing docs for any package would have activated it. These tests pin the
behaviour so it cannot return when that list fills up.

Refusal tests are paired with POSITIVE CONTROLS, so no assertion can pass merely
because the thing it looks for is absent.
"""

import os

import pytest

from apps.workspace.docs_app._context_builders import _resolve_doc_page
from apps.workspace.docs_app._sphinx import extract_sphinx_body

SECRET = "SUPERSECRET-do-not-disclose"


@pytest.fixture
def doc_base(tmp_path):
    """A docs dir, a secret OUTSIDE it, and a symlink inside pointing out."""
    base = tmp_path / "docs"
    base.mkdir()
    (base / "index.html").write_text('<div role="main"><p>REAL DOC</p></div>')
    (tmp_path / "secret.txt").write_text(SECRET)
    os.symlink(tmp_path / "secret.txt", base / "link.txt")
    return base


def test_escape_target_is_readable_without_containment(doc_base):
    """RED-EQUIVALENT: proves the refusal tests are not passing vacuously."""
    # Arrange
    escaped = doc_base / "../secret.txt"
    # Act
    reachable = escaped.is_file()
    # Assert
    assert reachable is True


def test_planted_symlink_really_points_outside(doc_base):
    """RED-EQUIVALENT for the symlink case specifically."""
    # Arrange
    link = doc_base / "link.txt"
    # Act
    content = link.read_text()
    # Assert
    assert content == SECRET


@pytest.mark.parametrize(
    "page_file",
    [
        "../secret.txt",
        "../../etc/hostname",
        "/etc/hostname",
        "link.txt",  # symlink planted INSIDE doc_base, resolving outside
    ],
)
def test_paths_escaping_doc_base_are_refused(doc_base, page_file):
    # Arrange
    base = doc_base
    # Act
    resolved = _resolve_doc_page(base, page_file)
    # Assert
    assert resolved is None


def test_legitimate_page_still_resolves(doc_base):
    """POSITIVE CONTROL — containment must not break ordinary docs."""
    # Arrange
    base = doc_base
    # Act
    resolved = _resolve_doc_page(base, "index.html")
    # Assert
    assert resolved is not None


def test_legitimate_page_resolves_to_the_requested_file(doc_base):
    # Arrange
    base = doc_base
    # Act
    resolved = _resolve_doc_page(base, "index.html")
    # Assert
    assert resolved.name == "index.html"


def test_missing_page_is_refused_rather_than_raising(doc_base):
    # Arrange
    base = doc_base
    # Act
    resolved = _resolve_doc_page(base, "no-such-page.html")
    # Assert
    assert resolved is None


def test_extractor_does_not_echo_non_html_content():
    """Defence in depth: a plain-text file must not be returned verbatim."""
    # Arrange
    plain_text = f"root:x:0:0\n{SECRET}\n"
    # Act
    body = extract_sphinx_body(plain_text)
    # Assert
    assert SECRET not in body


def test_extractor_still_returns_real_documentation():
    """POSITIVE CONTROL — the hardening must not blank out real docs."""
    # Arrange
    page = '<div role="main"><p>REAL DOC</p></div>'
    # Act
    body = extract_sphinx_body(page)
    # Assert
    assert "REAL DOC" in body


def test_extractor_passes_through_html_lacking_role_main():
    """Sphinx themes without role="main" must still render (no degrade)."""
    # Arrange
    page = "<html><body>THEME BODY</body></html>"
    # Act
    body = extract_sphinx_body(page)
    # Assert
    assert "THEME BODY" in body
