#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Keyboard shortcuts data for SciTeX.

Contains keyboard shortcut definitions organized by context.
The English strings here are the gettext msgids (SSoT);
:func:`translated_shortcuts_data` produces a per-request, active-language
deep copy for the view.
"""

import copy

from django.utils.translation import gettext as _

# Keyboard shortcuts data organized by context
KEYBOARD_SHORTCUTS_DATA = [
    {
        "name": "Global",
        "slug": "global",
        "icon": "🌐",
        "description": "Available everywhere in SciTeX",
        "sections": [
            {
                "title": "Global Navigation",
                "shortcuts": [
                    {"keys": "Alt+F", "description": "Files"},
                    {"keys": "Alt+S", "description": "Scholar"},
                    {"keys": "Alt+V", "description": "Visualizer"},
                    {"keys": "Alt+W", "description": "Writer"},
                    {"keys": "Alt+Z", "description": "Zen Mode"},
                ],
            },
        ],
    },
    {
        "name": "Files",
        "slug": "files",
        "icon": "📁",
        "description": "File browser",
        "sections": [
            {
                "title": "Navigation",
                "shortcuts": [
                    {"keys": "Enter", "description": "Open item"},
                    {"keys": "Backspace", "description": "Parent folder"},
                    {"keys": "/", "description": "Focus search"},
                ],
            },
            {
                "title": "File Actions",
                "shortcuts": [
                    {"keys": "Ctrl+N", "description": "New file"},
                    {"keys": "Ctrl+Shift+N", "description": "New folder"},
                    {"keys": "F2", "description": "Rename"},
                    {"keys": "Del", "description": "Delete"},
                ],
            },
        ],
    },
    {
        "name": "Scholar",
        "slug": "scholar",
        "icon": "🎓",
        "description": "Literature search",
        "sections": [
            {
                "title": "Search",
                "shortcuts": [
                    {"keys": "Ctrl+F", "description": "Focus search"},
                    {"keys": "Enter", "description": "Search"},
                ],
            },
            {
                "title": "Citations",
                "shortcuts": [
                    {"keys": "Ctrl+S", "description": "Save to library"},
                    {"keys": "Ctrl+C", "description": "Copy citation"},
                ],
            },
        ],
    },
    {
        "name": "Visualizer",
        "slug": "vis",
        "icon": "📊",
        "description": "Figure editor",
        "sections": [
            {
                "title": "Basic",
                "shortcuts": [
                    {"keys": "Ctrl+C", "description": "Copy object"},
                    {"keys": "Ctrl+V", "description": "Paste object"},
                    {"keys": "Ctrl+D", "description": "Duplicate"},
                    {"keys": "Ctrl+Z", "description": "Undo"},
                    {"keys": "Ctrl+Y", "description": "Redo"},
                    {"keys": "Del", "description": "Delete selected"},
                    {"keys": "Arrow", "description": "Move 1px"},
                    {"keys": "Shift+Arrow", "description": "Move 10px"},
                ],
            },
            {
                "title": "Align (Alt+A → ...)",
                "shortcuts": [
                    {"keys": "L", "description": "Left"},
                    {"keys": "R", "description": "Right"},
                    {"keys": "T", "description": "Top"},
                    {"keys": "B", "description": "Bottom"},
                    {"keys": "H", "description": "Distribute H (equal)"},
                    {"keys": "V", "description": "Distribute V (equal)"},
                    {"keys": "C", "description": "Center horizontal"},
                    {"keys": "M", "description": "Center vertical"},
                ],
            },
            {
                "title": "Align by Axis (Alt+Shift+A → ...)",
                "shortcuts": [
                    {"keys": "L", "description": "Y-Axis (Left edge)"},
                    {"keys": "R", "description": "Right edge"},
                    {"keys": "T", "description": "Top edge"},
                    {"keys": "B", "description": "X-Axis (Bottom edge)"},
                    {"keys": "C", "description": "Horizontal center"},
                    {"keys": "M", "description": "Vertical center"},
                    {"keys": "S", "description": "Stack vertically"},
                ],
            },
            {
                "title": "Size (Alt+Z → ...)",
                "shortcuts": [
                    {"keys": "S", "description": "Match Size"},
                    {"keys": "W", "description": "Match Width"},
                    {"keys": "T", "description": "Match Height (Tall)"},
                    {"keys": "C", "description": "Multiple Crop"},
                ],
            },
            {
                "title": "Arrange",
                "shortcuts": [
                    {"keys": "Alt+F", "description": "Bring to Front"},
                    {"keys": "Alt+B", "description": "Send to Back"},
                ],
            },
            {
                "title": "View",
                "shortcuts": [
                    {"keys": "+", "description": "Zoom in"},
                    {"keys": "-", "description": "Zoom out"},
                    {"keys": "0", "description": "Fit to window"},
                    {"keys": "G", "description": "Toggle grid"},
                    {"keys": "Alt+T", "description": "Toggle theme"},
                ],
            },
            {
                "title": "Group",
                "shortcuts": [
                    {"keys": "Ctrl+G", "description": "Group"},
                    {"keys": "Ctrl+Shift+G", "description": "Ungroup"},
                ],
            },
        ],
    },
    {
        "name": "Writer",
        "slug": "writer",
        "icon": "✍️",
        "description": "Document editor",
        "sections": [
            {
                "title": "Document",
                "shortcuts": [
                    {"keys": "Ctrl+S", "description": "Save"},
                    {"keys": "Ctrl+B", "description": "Bold"},
                    {"keys": "Ctrl+I", "description": "Italic"},
                    {"keys": "Ctrl+K", "description": "Insert link"},
                ],
            },
            {
                "title": "Insert",
                "shortcuts": [
                    {"keys": "Ctrl+Shift+C", "description": "Citation"},
                    {"keys": "Ctrl+Shift+E", "description": "Equation"},
                    {"keys": "Ctrl+Shift+F", "description": "Figure"},
                ],
            },
        ],
    },
]


def translated_shortcuts_data():
    """Per-request, active-language deep copy of KEYBOARD_SHORTCUTS_DATA.

    The module-level KEYBOARD_SHORTCUTS_DATA holds the English msgids (the SSoT).
    This function deep-copies it and translates every user-visible display field
    (name, description, title — the ones the template renders) with the
    *current* active language, so a request rendered under the ja locale gets
    Japanese and under en-us gets English. The keys (functional: Alt+F,
    Ctrl+Shift+N, …), icons (emoji), and slugs are left untouched — they are
    not translatable.
    """
    data = copy.deepcopy(KEYBOARD_SHORTCUTS_DATA)
    for ctx in data:
        ctx["name"] = _(ctx["name"])
        ctx["description"] = _(ctx["description"])
        for section in ctx["sections"]:
            section["title"] = _(section["title"])
            for shortcut in section["shortcuts"]:
                shortcut["description"] = _(shortcut["description"])
    return data


# EOF
