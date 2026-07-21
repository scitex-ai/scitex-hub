#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for the recruit page (/recruit/).

Public, unauthenticated OSS-contributor recruitment page (students
welcome). Copy is legally reviewed:

- The ONLY current offering is voluntary OSS contribution — never
  phrased as unpaid work for the company (no 無給 / "unpaid" wording).
- University-credit internships and paid roles appear ONLY as future
  items under これから始めるもの / Coming next.
- Contact email: recruit@scitex.ai (operator-decided 2026-07-22).
"""

import pytest
from django.urls import reverse


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

    def test_recruit_page_shows_japanese_heading(self, client):
        # Arrange
        url = reverse("public_app:recruit")
        # Act
        content = client.get(url).content.decode("utf-8")
        # Assert
        assert "一緒に、研究の速度を上げませんか" in content

    def test_recruit_page_shows_english_heading(self, client):
        # Arrange
        url = reverse("public_app:recruit")
        # Act
        content = client.get(url).content.decode("utf-8")
        # Assert
        assert "Build the tools that speed up science" in content

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
        # Arrange: operator-decided address (2026-07-22)
        url = reverse("public_app:recruit")
        # Act
        content = client.get(url).content.decode("utf-8")
        # Assert
        assert "recruit@scitex.ai" in content

    @pytest.mark.parametrize("heading", ["これから始めるもの", "Coming next"])
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
