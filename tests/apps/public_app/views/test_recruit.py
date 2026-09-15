#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for the recruit page (/recruit/).

Public, unauthenticated OSS-contributor recruitment page (students
welcome). Copy is legally reviewed:

- The ONLY current offering is voluntary OSS contribution — never
  phrased as unpaid work for the company (no 無給 / "unpaid" wording).
- University-credit internships and paid roles appear ONLY as future
  items under "Coming next" (JA: これから始めるもの).
- Contact email: ``branding.RECRUIT_EMAIL`` (operator-decided 2026-07-22).
  The template injects it via the ``site_branding`` context processor, so this
  file reads the constant too — a test that repeated the literal would be one
  more place to edit, and would keep passing against a stale page.
"""

import pytest
from django.urls import reverse

from config import branding


@pytest.mark.django_db
class TestRecruitPage:
    """/recruit/ — OSS contributor recruitment page."""

    def test_recruit_page_returns_http_200_unauthenticated(self, client):
        # Arrange: anonymous client (page must be public)
        url = reverse("public_app:recruit")
        # Act
        response = client.get(url)
        # Assert
        assert response.status_code == 200

    def test_recruit_page_uses_recruit_template(self, client):
        # Arrange
        url = reverse("public_app:recruit")
        # Act
        response = client.get(url)
        # Assert
        templates = [t.name for t in response.templates if t.name]
        assert "public_app/pages/recruit.html" in templates

    def test_recruit_page_defaults_to_english_heading(self, client):
        # Arrange: no language cookie, so the English source renders
        url = reverse("public_app:recruit")
        # Act
        content = client.get(url).content.decode("utf-8")
        # Assert
        assert "Speed up research with us" in content

    def test_recruit_page_default_omits_hardcoded_japanese(self, client):
        # Arrange: Japanese appears only via the ja catalog
        url = reverse("public_app:recruit")
        # Act
        content = client.get(url).content.decode("utf-8")
        # Assert
        assert "一緒に、研究の速度を上げませんか" not in content

    def test_recruit_heading_has_japanese_translation(self):
        # Arrange: the Japanese copy lives in the catalog, not the template
        from pathlib import Path

        from django.conf import settings

        po_path = Path(settings.BASE_DIR, "locale/ja/LC_MESSAGES/django.po")
        # Act
        po = po_path.read_text(encoding="utf-8")
        # Assert
        assert (
            'msgid "Speed up research with us"\n'
            'msgstr "一緒に、研究の速度を上げませんか"' in po
        )

    def test_recruit_page_mentions_good_first_issue(self, client):
        # Arrange
        url = reverse("public_app:recruit")
        # Act
        content = client.get(url).content.decode("utf-8")
        # Assert
        assert "good first issue" in content

    def test_recruit_page_links_github_org(self, client):
        # Arrange
        url = reverse("public_app:recruit")
        # Act
        content = client.get(url).content.decode("utf-8")
        # Assert
        assert "https://github.com/scitex-ai" in content

    def test_recruit_page_links_good_first_issue_search(self, client):
        # Arrange: org-wide open good-first-issue search on GitHub
        url = reverse("public_app:recruit")
        # Act
        content = client.get(url).content.decode("utf-8")
        # Assert
        assert (
            "https://github.com/search?q=org%3Ascitex-ai"
            "+label%3A%22good+first+issue%22+state%3Aopen" in content
        )

    def test_recruit_page_shows_contact_email(self, client):
        # Arrange: operator-decided address (2026-07-22), single-sourced in
        # config/branding.py and injected by the site_branding context
        # processor — the template holds no literal to fall back on.
        url = reverse("public_app:recruit")
        # Act
        content = client.get(url).content.decode("utf-8")
        # Assert
        assert branding.RECRUIT_EMAIL in content

    @pytest.mark.parametrize("heading", ["Coming next"])
    def test_recruit_page_lists_future_items_section_heading(self, client, heading):
        # Arrange: internships / paid roles may appear ONLY as future
        # items under these headings (legal review)
        url = reverse("public_app:recruit")
        # Act
        content = client.get(url).content.decode("utf-8")
        # Assert
        assert heading in content

    @pytest.mark.parametrize("banned", ["無給", "unpaid"])
    def test_recruit_page_never_phrases_unpaid_work(self, client, banned):
        # Arrange: legal guard — voluntary OSS contribution must never be
        # phrased as unpaid work for the company
        url = reverse("public_app:recruit")
        # Act
        content = client.get(url).content.decode("utf-8")
        # Assert
        assert banned not in content.lower()

    def test_footer_links_to_recruit(self, client):
        # Arrange: footer is global — a lightweight public page carries it
        url = reverse("public_app:about")
        # Act
        content = client.get(url).content.decode("utf-8")
        # Assert
        assert reverse("public_app:recruit") in content


if __name__ == "__main__":
    import os

    import pytest

    pytest.main([os.path.abspath(__file__)])

# EOF
