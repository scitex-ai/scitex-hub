#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for API Documentation Configuration."""

import pytest

from apps.infra.public_app.config import (
    API_DOC_DEFAULT_SECTION,
    API_DOC_SECTION_ORDER,
    API_DOC_SECTIONS,
    get_all_sections,
    get_all_subsection_ids,
    get_section,
)


class TestAPIDocSections:
    """Test API documentation section configuration."""

    def test_all_sections_have_required_fields(self):
        """Each section must have title, template, and subsections."""
        for key, section in API_DOC_SECTIONS.items():
            assert "title" in section, f"Section {key} missing title"
            assert "template" in section, f"Section {key} missing template"
            assert "subsections" in section, f"Section {key} missing subsections"

    def test_all_subsections_have_required_fields(self):
        """Each subsection must have id, title, and emoji."""
        for section_key, section in API_DOC_SECTIONS.items():
            for sub in section["subsections"]:
                assert "id" in sub, f"Subsection in {section_key} missing id"
                assert "title" in sub, f"Subsection in {section_key} missing title"
                assert "emoji" in sub, f"Subsection in {section_key} missing emoji"

    def test_section_order_matches_sections(self):
        """All sections in order list must exist in sections dict."""
        for key in API_DOC_SECTION_ORDER:
            assert (
                key in API_DOC_SECTIONS
            ), f"Section {key} in order but not in sections"

    def test_all_sections_in_order(self):
        """All sections must be in the order list."""
        for key in API_DOC_SECTIONS:
            assert key in API_DOC_SECTION_ORDER, f"Section {key} not in order list"

    def test_default_section_exists(self):
        """Default section must exist."""
        assert API_DOC_DEFAULT_SECTION in API_DOC_SECTIONS

    def test_get_section_returns_correct_section(self):
        """get_section should return the correct section."""
        section = get_section("getting-started")
        assert section is not None
        assert "🚀" in section["title"]

    def test_get_section_returns_none_for_invalid(self):
        """get_section should return None for invalid key."""
        assert get_section("nonexistent") is None

    def test_get_all_sections_returns_ordered_list(self):
        """get_all_sections should return sections in order."""
        sections = get_all_sections()
        assert len(sections) == len(API_DOC_SECTION_ORDER)
        for i, key in enumerate(API_DOC_SECTION_ORDER):
            assert sections[i]["key"] == key

    def test_get_all_subsection_ids_returns_all_ids(self):
        """get_all_subsection_ids should return all subsection IDs."""
        ids = get_all_subsection_ids()
        # Count expected IDs
        expected_count = sum(
            len(section["subsections"]) for section in API_DOC_SECTIONS.values()
        )
        assert len(ids) == expected_count

    def test_subsection_ids_are_unique(self):
        """All subsection IDs should be unique."""
        ids = get_all_subsection_ids()
        assert len(ids) == len(set(ids)), "Duplicate subsection IDs found"

    def test_templates_follow_naming_convention(self):
        """Templates should follow the naming convention."""
        for key, section in API_DOC_SECTIONS.items():
            template = section["template"]
            assert template.startswith("public_app/pages/api-docs-partials/")
            assert template.endswith(".html")


@pytest.fixture
def client():
    """Django test client (without pytest-django dependency)."""
    from django.test import Client

    return Client()


class TestAPIDocURLs:
    """Test API documentation URL generation."""

    def test_section_urls_are_valid(self, client):
        """Each section URL should return 200."""
        for key in API_DOC_SECTION_ORDER:
            response = client.get(f"/docs/web-api/{key}/")
            assert (
                response.status_code == 200
            ), f"Section {key} returned {response.status_code}"

    def test_main_api_docs_url(self, client):
        """Main API docs URL should return 200."""
        response = client.get("/docs/web-api/")
        assert response.status_code == 200

    def test_invalid_section_redirects_to_default(self, client):
        """Invalid section should show default section."""
        response = client.get("/docs/web-api/nonexistent/")
        assert response.status_code == 200
        # Should show getting-started content
        assert b"Introduction" in response.content


class TestCampaignTokens:
    """Test campaign token utilities."""

    def test_generate_campaign_token_format(self):
        """Generated token should follow standard format."""
        from datetime import datetime

        from apps.infra.public_app.config import generate_campaign_token

        start = datetime(2025, 2, 1)
        end = datetime(2025, 3, 31)
        token = generate_campaign_token(start, end, "alpha")
        assert token == "scitex-hub-campaign-20250201-20250331-alpha"

    def test_generate_campaign_token_sanitizes_hashtag(self):
        """Hashtag should be sanitized (lowercase, no special chars)."""
        from datetime import datetime

        from apps.infra.public_app.config import generate_campaign_token

        start = datetime(2025, 1, 1)
        end = datetime(2025, 12, 31)
        token = generate_campaign_token(start, end, "Test@Campaign#2025!")
        assert token == "scitex-hub-campaign-20250101-20251231-testcampaign2025"

    def test_parse_campaign_token_valid(self):
        """Parsing valid token should return components."""
        from apps.infra.public_app.config import parse_campaign_token

        result = parse_campaign_token("scitex-hub-campaign-20260101-20261231-alpha")
        assert result is not None
        assert result["hashtag"] == "alpha"
        assert result["start_date"].year == 2026
        assert result["start_date"].month == 1
        assert result["end_date"].month == 12

    def test_parse_campaign_token_invalid(self):
        """Parsing invalid token should return None."""
        from apps.infra.public_app.config import parse_campaign_token

        assert parse_campaign_token("invalid-token") is None
        assert parse_campaign_token("scitex-campaign-20250101-alpha") is None
        assert parse_campaign_token("") is None

    def test_is_valid_campaign_token(self):
        """Validation should correctly identify valid/invalid tokens."""
        from apps.infra.public_app.config import is_valid_campaign_token

        assert is_valid_campaign_token("scitex-hub-campaign-20260101-20261231-alpha")
        assert is_valid_campaign_token(
            "scitex-hub-campaign-20261201-20270131-beta-test"
        )
        assert not is_valid_campaign_token("invalid")
        assert not is_valid_campaign_token("scitex-alpha-key")

    def test_parse_legacy_campaign_token_alias(self):
        """Legacy scitex-cloud-campaign-* tokens are accepted (ADR-0001)."""
        import warnings

        from apps.infra.public_app.config import parse_campaign_token

        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            result = parse_campaign_token(
                "scitex-cloud-campaign-20260101-20261231-alpha"
            )
        assert result is not None, "legacy alias must still parse"
        assert result["hashtag"] == "alpha"
        assert result["legacy_format"] is True
        # No silent fallback: a DeprecationWarning must be emitted.
        assert any(
            issubclass(w.category, DeprecationWarning) for w in caught
        ), "legacy prefix should emit DeprecationWarning"

    def test_is_valid_campaign_token_accepts_legacy_alias(self):
        """is_valid_campaign_token should accept the legacy alias too."""
        from apps.infra.public_app.config import is_valid_campaign_token

        assert is_valid_campaign_token("scitex-cloud-campaign-20260101-20261231-alpha")

    def test_generate_campaign_token_never_emits_legacy_prefix(self):
        """The generator must only emit the current scitex-hub prefix."""
        from datetime import datetime

        from apps.infra.public_app.config import generate_campaign_token

        token = generate_campaign_token(
            datetime(2025, 1, 1), datetime(2025, 12, 31), "alpha"
        )
        assert token.startswith("scitex-hub-campaign-")
        assert "scitex-cloud" not in token

    def test_campaign_tokens_have_required_fields(self):
        """Campaign tokens config should have required fields."""
        from apps.infra.public_app.config import CAMPAIGN_TOKENS

        for key, info in CAMPAIGN_TOKENS.items():
            assert "token" in info, f"Campaign {key} missing token"
            assert "description" in info, f"Campaign {key} missing description"
            assert "permissions" in info, f"Campaign {key} missing permissions"

    def test_get_active_campaign_token(self):
        """Should return active campaign token or None."""
        from apps.infra.public_app.config import get_active_campaign_token

        # Function should return string or None
        result = get_active_campaign_token()
        assert result is None or isinstance(result, str)
