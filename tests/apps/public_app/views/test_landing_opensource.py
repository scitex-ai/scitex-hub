#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for the landing open-source + research-demo section (owner ask 2026-09-27).

The landing page carries a section about the open-source organisation
(github.com/scitex-ai) and its packages, plus the 40-minute research demo
block. No mocks — real Django test DB + test client. One assertion per test
(STX-TQ007).
"""

from django.test import TestCase

from apps.infra.public_app.views.landing import (
    RESEARCH_DEMO_POSTER_URL,
    RESEARCH_DEMO_VIDEO_URL,
)


class LandingOpenSourceSectionTest(TestCase):
    """The open-source section renders on the marketing landing."""

    def test_open_source_section_anchor_present(self):
        # Arrange: an anonymous visitor
        # Act
        resp = self.client.get("/landing/")
        # Assert — the section carries its anchor
        assert b'id="open-source"' in resp.content

    def test_org_link_present(self):
        # Arrange: an anonymous visitor
        # Act
        resp = self.client.get("/landing/")
        # Assert — the scitex-ai organisation is linked
        assert b"https://github.com/scitex-ai" in resp.content

    def test_open_source_page_linked(self):
        # Arrange: an anonymous visitor
        # Act
        resp = self.client.get("/landing/")
        # Assert — the section points at the /open-source/ page
        assert b'href="/open-source/"' in resp.content

    def test_package_hub_linked(self):
        # Arrange: an anonymous visitor
        # Act
        resp = self.client.get("/landing/")
        # Assert
        assert b"https://github.com/scitex-ai/scitex-hub" in resp.content

    def test_package_agent_container_linked(self):
        # Arrange: an anonymous visitor
        # Act
        resp = self.client.get("/landing/")
        # Assert
        assert b"https://github.com/scitex-ai/scitex-agent-container" in resp.content

    def test_package_cards_linked(self):
        # Arrange: an anonymous visitor
        # Act
        resp = self.client.get("/landing/")
        # Assert
        assert b"https://github.com/scitex-ai/scitex-cards" in resp.content

    def test_package_storage_linked(self):
        # Arrange: an anonymous visitor
        # Act
        resp = self.client.get("/landing/")
        # Assert
        assert b"https://github.com/scitex-ai/scitex-storage" in resp.content

    def test_package_scholar_linked(self):
        # Arrange: an anonymous visitor
        # Act
        resp = self.client.get("/landing/")
        # Assert
        assert b"https://github.com/scitex-ai/scitex-scholar" in resp.content

    def test_package_writer_linked(self):
        # Arrange: an anonymous visitor
        # Act
        resp = self.client.get("/landing/")
        # Assert
        assert b"https://github.com/scitex-ai/scitex-writer" in resp.content

    def test_package_sdk_linked(self):
        # Arrange: an anonymous visitor
        # Act
        resp = self.client.get("/landing/")
        # Assert
        assert b"https://github.com/scitex-ai/scitex-sdk" in resp.content


class LandingResearchDemoBlockTest(TestCase):
    """The 40-minute research demo block uses the native video embed."""

    def test_research_demo_anchor_present(self):
        # Arrange: an anonymous visitor
        # Act
        resp = self.client.get("/landing/")
        # Assert — the demo block carries its anchor
        assert b'id="research-demo"' in resp.content

    def test_demo_video_uses_native_embed_with_controls(self):
        # Arrange: an anonymous visitor
        # Act
        resp = self.client.get("/landing/")
        # Assert — owner's preferred native embed style: autoplay muted loop + controls
        assert b"<video autoplay" in resp.content and b"controls" in resp.content

    def test_demo_video_loop_muted_playsinline(self):
        # Arrange: an anonymous visitor
        # Act
        resp = self.client.get("/landing/")
        # Assert — the embed loops silently inline like the module demos
        body = resp.content
        assert b"loop" in body and b"muted" in body and b"playsinline" in body

    def test_demo_video_src_is_research_demo_url(self):
        # Arrange: the 40-minute demo is the scitex-automated-research media file
        # Act
        resp = self.client.get("/landing/")
        # Assert — the player embeds the real demo URL
        assert RESEARCH_DEMO_VIDEO_URL.encode() in resp.content

    def test_demo_poster_is_research_demo_thumbnail(self):
        # Arrange: the catalog thumbnail for the same demo
        # Act
        resp = self.client.get("/landing/")
        # Assert — the poster attribute carries the real thumbnail URL
        assert RESEARCH_DEMO_POSTER_URL.encode() in resp.content

    def test_demo_url_is_the_real_media_file(self):
        # Arrange: the module-level demo URL constant
        # Act
        actual = RESEARCH_DEMO_VIDEO_URL
        # Assert — no placeholder survives; it is the owner-confirmed media URL
        assert actual == "https://scitex.ai/media/videos/scitex-automated-research-demo.mp4"

    def test_demo_video_matches_catalog_entry(self):
        # Arrange: the VIDEO_CATALOG entry the watch page serves
        # Act
        from apps.infra.public_app.views.pages_data import VIDEO_CATALOG

        entry_url = VIDEO_CATALOG["scitex-automated-research"]["url"]
        # Assert — the landing embed and the catalog serve the same file
        assert RESEARCH_DEMO_VIDEO_URL.endswith(entry_url)

    def test_more_demo_videos_linked(self):
        # Arrange: an anonymous visitor
        # Act
        resp = self.client.get("/landing/")
        # Assert — overflow goes to the demos index (owner: never per-movie URLs)
        assert b'href="/demos/"' in resp.content

    def test_no_per_movie_demo_links(self):
        # Arrange: an anonymous visitor (owner correction 2026-09-27: the
        # section links the demos index, not individual demo movies)
        # Act
        resp = self.client.get("/landing/")
        # Assert — no per-movie watch URL appears in the new section
        assert b'href="/demos/watch/' not in resp.content

    def test_sdk_custom_app_demo_slot_reserved(self):
        # Arrange: an anonymous visitor
        # Act
        resp = self.client.get("/landing/")
        # Assert — the SDK custom-app demo slot is a marked coming-soon note
        assert b"scitex-sdk GUI" in resp.content


class LandingAppStoreNoteTest(TestCase):
    """The App Store section notes future native mobile stores as planned."""

    def test_native_mobile_stores_noted_as_planned(self):
        # Arrange: an anonymous visitor
        # Act
        resp = self.client.get("/landing/")
        # Assert — forward-looking line, not a promise of availability
        assert b"not yet available" in resp.content


if __name__ == "__main__":
    import os

    import pytest

    pytest.main([os.path.abspath(__file__)])

# EOF
