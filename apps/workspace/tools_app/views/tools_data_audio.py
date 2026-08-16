#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Research Tools data - Audio domain tools."""

from __future__ import annotations

# Audio tools (alphabetical by name)
AUDIO_TOOLS = [
    {
        "name": "Transcribe Audio",
        "description": "Turn a recording into text, on our own hardware. Japanese and English are auto-detected.",
        "use_case": "Transcribe an interview, a seminar recording, or a spoken note",
        # The app is mounted at "apps/" (config/urls.py), so the served path is
        # /apps/tools/... — `reverse("tools_app:tool_transcribe_audio")` returns exactly
        # this. The sibling domains all advertise a bare "/tools/..." instead, which does
        # NOT reach the tool; see the card referenced in the PR. Matching reverse() rather
        # than matching the neighbours, because the neighbours are the ones that are wrong.
        "bookmarklet_url": "/apps/tools/transcribe-audio/",
        "icon": "🎙️",
    },
]


# EOF
