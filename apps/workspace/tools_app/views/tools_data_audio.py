#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Research Tools data - Audio domain tools."""

from __future__ import annotations

# Audio tools (alphabetical by name)
AUDIO_TOOLS = [
    {
        "name": "Transcribe Audio",
        "slug": "transcribe-audio",
        "description": "Turn a recording into text, on our own hardware. Japanese and English are auto-detected.",
        "use_case": "Transcribe an interview, a seminar recording, or a spoken note",
        # The app is mounted at "apps/" (config/urls.py), so the served path is
        # /apps/tools/..., which is what reverse("tools_app:tool_transcribe_audio")
        # returns. Every sibling domain uses the same prefix.
        "bookmarklet_url": "/apps/tools/transcribe-audio/",
        "icon": "🎙️",
    },
]


# EOF
