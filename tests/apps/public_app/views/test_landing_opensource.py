#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for the landing open-source + research-demo section (owner ask 2026-09-27).

The landing page carries a section about the open-source organisation
(github.com/scitex-ai) and its packages, plus the 40-minute research demo
block. No mocks — real Django test DB + test client. One assertion per test
(STX-TQ007).
"""

from html.parser import HTMLParser
from urllib.parse import urlsplit

from django.test import TestCase

from apps.infra.public_app.views.landing import (
    RESEARCH_DEMO_POSTER_URL,
    RESEARCH_DEMO_VIDEO_URL,
)


def _linked_hosts(content):
    """Inspect actual hyperlink hostnames rather than URL-shaped substrings."""

    class Links(HTMLParser):
        def __init__(self):
            super().__init__()
            self.hosts = set()

        def handle_starttag(self, tag, attrs):
            if tag == "a":
                url = urlsplit(dict(attrs).get("href") or "")
                if url.scheme in {"http", "https"} and url.hostname:
                    self.hosts.add(url.hostname)

    links = Links()
    links.feed(content.decode())
    return links.hosts


def test_link_host_inspection_distinguishes_actual_hosts_from_substrings():
    content = (
        b'<a href="https://github.com/scitex-ai">GitHub</a>'
        b'<a href="https://github.com.evil.example/apps.apple.com">Other</a>'
        b'<a href="https://example.org/?next=https://play.google.com/store">Query</a>'
        b"<span>https://apps.apple.com</span>"
    )
    assert _linked_hosts(content) == {
        "github.com",
        "github.com.evil.example",
        "example.org",
    }


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

    def test_demo_video_is_visible_with_native_controls(self):
        # Arrange: an anonymous visitor
        # Act
        resp = self.client.get("/landing/")
        # Assert — the workflow video is visible with native controls, no disclosure.
        demo = resp.content.split(b'id="research-demo"', 1)[1].split(b"</details>", 1)[
            0
        ]
        assert (b"<summary" in demo, b"controls" in demo) == (False, True)

    def test_demo_video_is_manual_inline_without_autoplay_or_loop(self):
        # Arrange: an anonymous visitor
        # Act
        resp = self.client.get("/landing/")
        # Assert — no automatic playback or download of the full workflow.
        demo = resp.content.split(b'id="research-demo"', 1)[1].split(b"</details>", 1)[
            0
        ]
        assert (
            b"autoplay" in demo,
            b"loop" in demo,
            b"playsinline" in demo,
            b'preload="none"' in demo,
        ) == (False, False, True, True)

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
        assert (
            actual
            == "https://scitex.ai/media/videos/scitex-automated-research-demo.mp4"
        )

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

    def test_full_workflow_has_no_retired_disclosure_summary(self):
        # Arrange: an anonymous visitor
        # Act
        resp = self.client.get("/landing/")
        # Assert — no stale promise is substituted for the real manual video.
        assert b"Watch the full workflow" not in resp.content


class LandingAppStoreNoteTest(TestCase):
    """The App Store section notes future native mobile stores as planned."""

    def test_open_source_section_links_repositories_without_claiming_native_stores(
        self,
    ):
        # Arrange: an anonymous visitor
        # Act
        resp = self.client.get("/landing/")
        section = resp.content.split(b'id="open-source"', 1)[1].split(b"</section>", 1)[
            0
        ]
        # Assert — the current source section promises inspectable repositories.
        hosts = _linked_hosts(section)
        assert (
            "github.com" in hosts,
            "apps.apple.com" in hosts,
            "play.google.com" in hosts,
        ) == (True, False, False)


if __name__ == "__main__":
    import os

    import pytest

    pytest.main([os.path.abspath(__file__)])

# EOF
