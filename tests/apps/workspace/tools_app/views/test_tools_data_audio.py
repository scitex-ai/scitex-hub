#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for apps/workspace/tools_app/views/tools_data_audio.py

The Audio domain is a new tools category. These guard the two things that make it
reachable at all: that it is registered among the tool domains, and that its tool
points at a URL the router actually serves. A category that is defined but not
registered, or registered but linking to a 404, would look correct in the source
and be invisible or broken on the page.
"""

from django.urls import reverse

from apps.workspace.tools_app.views.tools_data import get_tool_domains
from apps.workspace.tools_app.views.tools_data_audio import AUDIO_TOOLS


class TestAudioDomainIsRegistered:
    """The Audio category must appear on the Tools page, not merely exist in a module."""

    def test_audio_domain_is_among_tool_domains(self):
        # Arrange
        domains = get_tool_domains()
        # Act
        slugs = [domain["slug"] for domain in domains]
        # Assert
        assert "audio" in slugs

    def test_audio_domain_carries_the_audio_tools(self):
        # Arrange
        domains = get_tool_domains()
        # Act
        audio = next(domain for domain in domains if domain["slug"] == "audio")
        # Assert
        assert audio["tools"] == AUDIO_TOOLS

    def test_audio_domain_is_not_empty(self):
        # Arrange
        domains = get_tool_domains()
        # Act
        audio = next(domain for domain in domains if domain["slug"] == "audio")
        # Assert
        assert len(audio["tools"]) > 0


class TestAudioToolLinksResolve:
    """Every Audio tool's advertised URL must be one the router serves."""

    def test_transcribe_audio_route_is_registered(self):
        # Arrange
        expected = "/tools/transcribe-audio/"
        # Act
        resolved = reverse("tools_app:tool_transcribe_audio")
        # Assert
        assert resolved == expected

    def test_every_audio_tool_url_is_served(self):
        # Arrange
        served = {reverse("tools_app:tool_transcribe_audio")}
        # Act
        advertised = {tool["bookmarklet_url"] for tool in AUDIO_TOOLS}
        # Assert
        assert advertised <= served


if __name__ == "__main__":
    import os

    import pytest

    pytest.main([os.path.abspath(__file__)])

# EOF
