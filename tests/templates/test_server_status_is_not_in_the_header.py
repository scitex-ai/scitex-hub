#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: tests/templates/test_server_status_is_not_in_the_header.py
"""The server-status icon is out of the header, and /server-status/ still works.

OPERATOR, Telegram 4864 / 4866 / 4869, 2026-09-05:
「サーバーステータスはヘッダーから外す」
「ショートカットもハンバーガーに逃がす…ハンバーガーがないとサーバーステータスは
  ですよねもありますね。なのでアイコンがいらないの」
「はい外してお願いします」

REMOVE THE ORNAMENT, KEEP THE PAGE. That distinction is the whole point of this
file: /server-status/ is still routed and still linked (the footer, and the
notification dropdown in the same header), and the tests below pin that, so
nobody "finishes the job" by deleting the view as well.

WHY A TEMPLATE-TEXT TEST AND NOT ONLY A RENDERED ONE. Both are here. The
rendered assertion is the one that describes what a user sees, and it needs a
database; the text assertion needs nothing and so still runs in environments
where the DB-backed suites are unavailable — which is the situation on the
development host today. Neither alone is enough: the text test would pass if
the markup moved to another partial that the header includes, and the rendered
test would pass vacuously if the page failed to render at all. The rendered
test therefore asserts something POSITIVE about the page as its control.
"""

from pathlib import Path

import pytest

# tests/templates/ -> repo root
_REPO_ROOT = Path(__file__).resolve().parents[2]
_HEADER = _REPO_ROOT / "templates" / "global_base_partials" / "global_header.html"

_REMOVED_IDS = ("server-status-indicator", "server-stx-shell-status-bar__btn")


def test_the_header_template_is_on_disk():
    """Control: a moved or renamed file would make the rest vacuous."""
    # Arrange
    path = _HEADER
    # Act
    present = path.is_file()
    # Assert
    assert present is True, f"no header template at {path}"


def test_the_header_declares_no_server_status_icon():
    # Arrange
    source = _HEADER.read_text(encoding="utf-8")
    # Act
    still_there = [
        element_id
        for element_id in _REMOVED_IDS
        if f'id="{element_id}"' in source
    ]
    # Assert
    assert still_there == [], f"header still declares {still_there}"


def test_the_header_still_links_the_status_page():
    """The page is not being removed — only its icon in the header."""
    # Arrange
    source = _HEADER.read_text(encoding="utf-8")
    # Act
    links = source.count("public_app:server_status")
    # Assert
    assert links >= 1, "the header dropped the status link entirely"


@pytest.fixture(name="rendered_body")
def _rendered_body(client, django_user_model):
    """The signed-in workspace page, as HTML."""
    user = django_user_model.objects.create_user(
        username="header-status-probe", password="x"
    )
    client.force_login(user)
    return client.get("/").content.decode("utf-8", "replace")


@pytest.mark.django_db
def test_the_page_renders_a_header_at_all(rendered_body):
    """Control for the two below: absence proves nothing on a blank page."""
    # Arrange
    body = rendered_body
    # Act
    has_header = "<header" in body
    # Assert
    assert has_header is True


@pytest.mark.django_db
def test_a_rendered_page_has_no_status_indicator(rendered_body):
    # Arrange
    element_id = "server-status-indicator"
    # Act
    present = f'id="{element_id}"' in rendered_body
    # Assert
    assert present is False


@pytest.mark.django_db
def test_a_rendered_page_has_no_status_button(rendered_body):
    # Arrange
    element_id = "server-stx-shell-status-bar__btn"
    # Act
    present = f'id="{element_id}"' in rendered_body
    # Assert
    assert present is False


@pytest.mark.django_db
def test_the_status_page_is_still_reachable(client, django_user_model):
    # Arrange
    user = django_user_model.objects.create_user(
        username="header-status-probe-2", password="x"
    )
    client.force_login(user)
    # Act
    resp = client.get("/server-status/")
    # Assert
    assert resp.status_code == 200


# EOF
