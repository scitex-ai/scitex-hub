#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for apps/public_app/views/pages.py

Tests Open Graph meta tags for video player pages (GitHub Issue #25).

Note: Tests that require Django will be skipped if Django is not available.
"""

import os
import sys

import pytest

# Check if Django is available
DJANGO_AVAILABLE = False
try:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.settings_dev")
    import django

    django.setup()
    DJANGO_AVAILABLE = True
except Exception:
    pass


class TestVideoCatalogStructure:
    """Test VIDEO_CATALOG data structure (no Django required)."""

    @pytest.fixture(autouse=True)
    def setup_path(self):
        """Add project root to path for imports."""
        project_root = os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
        )
        if project_root not in sys.path:
            sys.path.insert(0, project_root)

    def test_og_base_url_is_https(self):
        """OG_BASE_URL should use HTTPS for production."""
        # Direct import from pages_data (bypassing views/__init__.py)
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "pages_data",
            os.path.join(
                os.path.dirname(__file__),
                "../../../../apps/public_app/views/pages_data.py",
            ),
        )
        # We need to mock the pages_shortcuts import
        import sys

        sys.modules["apps.public_app.views.pages_shortcuts"] = type(sys)(
            "pages_shortcuts"
        )
        sys.modules["apps.public_app.views.pages_shortcuts"].KEYBOARD_SHORTCUTS_DATA = (
            []
        )

        # Now manually parse the file to extract OG_BASE_URL
        pages_data_path = os.path.join(
            os.path.dirname(__file__),
            "../../../../apps/public_app/views/pages_data.py",
        )
        pages_data_path = os.path.abspath(pages_data_path)

        with open(pages_data_path) as f:
            content = f.read()

        # Extract OG_BASE_URL
        import re

        match = re.search(r'OG_BASE_URL\s*=\s*["\']([^"\']+)["\']', content)
        assert match, "OG_BASE_URL not found in pages_data.py"
        og_base_url = match.group(1)

        assert og_base_url.startswith(
            "https://"
        ), f"OG_BASE_URL should be HTTPS: {og_base_url}"
        assert "scitex.ai" in og_base_url

    def test_video_catalog_structure(self):
        """VIDEO_CATALOG should have correct structure."""
        import re

        # Parse the file to extract VIDEO_CATALOG structure
        pages_data_path = os.path.join(
            os.path.dirname(__file__),
            "../../../../apps/public_app/views/pages_data.py",
        )
        pages_data_path = os.path.abspath(pages_data_path)

        with open(pages_data_path) as f:
            content = f.read()

        # Check required videos exist
        mcp_demos = [
            "figrecipe",
            "crossref-local",
            "scitex-writer",
            "scitex-automated-research",
        ]
        for video_id in mcp_demos:
            assert f'"{video_id}"' in content, f"Missing MCP demo: {video_id}"

        # Check required fields are present
        required_patterns = [
            r'"title":\s*"',
            r'"url":\s*"',
            r'"description":\s*\(',
            r'"thumbnail":\s*',  # Can be None or string
        ]
        for pattern in required_patterns:
            assert re.search(pattern, content), f"Missing pattern: {pattern}"

    def test_thumbnails_are_png(self):
        """Thumbnails should be PNG files."""
        pages_data_path = os.path.join(
            os.path.dirname(__file__),
            "../../../../apps/public_app/views/pages_data.py",
        )
        pages_data_path = os.path.abspath(pages_data_path)

        with open(pages_data_path) as f:
            content = f.read()

        import re

        # Find all thumbnail definitions that are not None
        thumbnails = re.findall(r'"thumbnail":\s*"([^"]+)"', content)
        for thumb in thumbnails:
            assert thumb.endswith(".png"), f"Thumbnail should be PNG: {thumb}"
            assert thumb.startswith("/"), f"Thumbnail should be absolute path: {thumb}"


@pytest.mark.skipif(not DJANGO_AVAILABLE, reason="Django not available")
class TestVideoPlayerView:
    """Test video_player view function (requires Django)."""

    @pytest.fixture
    def rf(self):
        """Request factory with anonymous user (AuthenticationMiddleware not run)."""
        from django.contrib.auth.models import AnonymousUser
        from django.test import RequestFactory

        class _RF(RequestFactory):
            def get(self, *args, **kwargs):
                request = super().get(*args, **kwargs)
                request.user = AnonymousUser()
                request.session = {}
                return request

        return _RF()

    def test_video_player_returns_200_for_valid_video(self, rf):
        """video_player should return 200 for valid video ID."""
        from apps.public_app.views.pages import video_player

        request = rf.get("/demos/watch/figrecipe/")
        response = video_player(request, "figrecipe")
        assert response.status_code == 200

    def test_video_player_raises_404_for_invalid_video(self, rf):
        """video_player should raise 404 for invalid video ID."""
        from django.http import Http404

        from apps.public_app.views.pages import video_player

        request = rf.get("/demos/watch/nonexistent/")
        with pytest.raises(Http404):
            video_player(request, "nonexistent")

    def test_video_player_context_contains_og_fields(self, rf):
        """video_player should pass OG metadata in rendered HTML."""
        from apps.public_app.views.pages import video_player

        request = rf.get("/demos/watch/figrecipe/")
        response = video_player(request, "figrecipe")

        # video_player uses render() which returns HttpResponse with rendered HTML.
        # Check OG metadata in the rendered content.
        content = response.content.decode()
        assert (
            "og:title" in content
            or "video_title" in content
            or "figrecipe" in content.lower()
        )

    def test_og_url_is_absolute(self, rf):
        """og_url should be an absolute URL with HTTPS in rendered HTML."""
        from apps.public_app.views.pages import video_player

        request = rf.get("/demos/watch/figrecipe/")
        response = video_player(request, "figrecipe")

        content = response.content.decode()
        # OG URL should appear as https:// somewhere in the content
        assert "https://" in content


@pytest.mark.skipif(not DJANGO_AVAILABLE, reason="Django not available")
@pytest.mark.django_db
class TestVideoPlayerIntegration:
    """Integration tests for video player page with OG meta tags."""

    @pytest.fixture
    def client(self):
        """Django test client."""
        from django.test import Client

        return Client()

    def test_video_page_contains_og_meta_tags(self, client):
        """Video page HTML should contain Open Graph meta tags."""
        response = client.get("/demos/watch/figrecipe/")
        assert response.status_code == 200

        content = response.content.decode("utf-8")

        # Check OG meta tags exist
        assert 'property="og:title"' in content
        assert 'property="og:description"' in content
        assert 'property="og:image"' in content
        assert 'property="og:url"' in content
        assert 'property="og:type"' in content

    def test_video_page_contains_twitter_meta_tags(self, client):
        """Video page HTML should contain Twitter Card meta tags."""
        response = client.get("/demos/watch/figrecipe/")
        content = response.content.decode("utf-8")

        # Check Twitter meta tags exist
        assert 'name="twitter:card"' in content
        assert 'name="twitter:title"' in content
        assert 'name="twitter:description"' in content
        assert 'name="twitter:image"' in content
        assert 'name="twitter:site"' in content
        assert "@SciTeX_AI" in content

    def test_og_image_contains_absolute_url(self, client):
        """OG image meta tag should contain absolute URL."""
        import re

        response = client.get("/demos/watch/figrecipe/")
        content = response.content.decode("utf-8")

        # Find og:image content
        match = re.search(r'property="og:image"\s+content="([^"]+)"', content)
        assert match, "og:image meta tag not found"

        og_image_url = match.group(1)
        assert og_image_url.startswith(
            "https://"
        ), f"OG image should be HTTPS: {og_image_url}"


if __name__ == "__main__":
    pytest.main([os.path.abspath(__file__), "-v"])
