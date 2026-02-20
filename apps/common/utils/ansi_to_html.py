#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ANSI Color Code to HTML Converter

Converts ANSI escape sequences and log-level prefixes to HTML spans
with semantic classes for proper color rendering in web terminals.

Used across all apps (writer, scholar, console, etc.)
"""

import re

# ANSI color code to CSS class mapping
ANSI_TO_CLASS = {
    # Regular colors
    "30": "ansi-black",
    "31": "ansi-red",
    "32": "ansi-green",
    "33": "ansi-yellow",
    "34": "ansi-blue",
    "35": "ansi-magenta",
    "36": "ansi-cyan",
    "37": "ansi-white",
    # Bright colors
    "90": "ansi-bright-black",
    "91": "ansi-bright-red",
    "92": "ansi-bright-green",
    "93": "ansi-bright-yellow",
    "94": "ansi-bright-blue",
    "95": "ansi-bright-magenta",
    "96": "ansi-bright-cyan",
    "97": "ansi-bright-white",
}


def ansi_to_html(text: str) -> str:
    """
    Convert ANSI escape sequences and log-level prefixes to HTML spans.

    Handles both:
    - ANSI escape codes (e.g., \\x1b[0;32m ... \\x1b[0m)
    - Log-level prefixes (e.g., [SUCCESS], [ERROR], SUCC:, ERRO:)

    Color mapping respects scitex.logging conventions:
    - SUCCESS/SUCC: -> green (highlight)
    - ERROR/ERRO/FAIL: -> red (highlight)
    - WARNING/WARN: -> yellow (highlight)
    - INFO: -> default text (no highlight, baseline level)
    - DEBUG/DBUG: -> muted (dimmed)

    Args:
        text: Text with ANSI codes or log-level prefixes

    Returns:
        HTML with semantic CSS classes for terminal-log rendering
    """
    if not text:
        return text

    # First pass: convert ANSI escape codes
    html = _convert_ansi_codes(text)

    # Second pass: colorize log-level prefixes (only for lines without ANSI spans)
    html = _colorize_log_prefixes(html)

    return html


def _convert_ansi_codes(text: str) -> str:
    """Convert ANSI escape sequences to HTML spans."""
    ansi_pattern = re.compile(r"\x1b\[([0-9;]+)m")

    result = []
    last_end = 0
    current_classes = []

    for match in ansi_pattern.finditer(text):
        if match.start() > last_end:
            text_segment = text[last_end : match.start()]
            if current_classes:
                result.append(
                    f"<span class='{' '.join(current_classes)}'>{escape_html(text_segment)}</span>"
                )
            else:
                result.append(escape_html(text_segment))

        codes = match.group(1).split(";")

        if "0" in codes or codes == [""]:
            current_classes = []
        else:
            for code in codes:
                if code in ANSI_TO_CLASS:
                    css_class = ANSI_TO_CLASS[code]
                    if css_class not in current_classes:
                        current_classes.append(css_class)

        last_end = match.end()

    if last_end < len(text):
        text_segment = text[last_end:]
        if current_classes:
            result.append(
                f"<span class='{' '.join(current_classes)}'>{escape_html(text_segment)}</span>"
            )
        else:
            result.append(escape_html(text_segment))

    return "".join(result)


# Log-level prefix patterns and their CSS classes
# Respects scitex.logging: INFO is baseline (no color), only highlight deviations
_LOG_LEVEL_PATTERNS = [
    # [SUCCESS] or SUCC: -> green
    (re.compile(r"^(\[SUCCESS\].*)$", re.MULTILINE), "ansi-green"),
    (re.compile(r"^(SUCC:\s*.*)$", re.MULTILINE), "ansi-green"),
    # [ERROR] or ERRO: -> red
    (re.compile(r"^(\[ERROR\].*)$", re.MULTILINE), "ansi-red"),
    (re.compile(r"^(ERRO:\s*.*)$", re.MULTILINE), "ansi-red"),
    # [FAIL] or FAIL: -> red
    (re.compile(r"^(\[FAIL\].*)$", re.MULTILINE), "ansi-red"),
    (re.compile(r"^(FAIL:\s*.*)$", re.MULTILINE), "ansi-red"),
    # [WARNING] or WARN: -> yellow
    (re.compile(r"^(\[WARNING\].*)$", re.MULTILINE), "ansi-yellow"),
    (re.compile(r"^(WARN:\s*.*)$", re.MULTILINE), "ansi-yellow"),
    # [DEBUG] or DBUG: -> muted
    (re.compile(r"^(\[DEBUG\].*)$", re.MULTILINE), "ansi-bright-black"),
    (re.compile(r"^(DBUG:\s*.*)$", re.MULTILINE), "ansi-bright-black"),
    # INFO: intentionally not colorized (baseline level = default text color)
]


def _colorize_log_prefixes(html: str) -> str:
    """Colorize lines with log-level prefixes that don't already have ANSI spans."""
    for pattern, css_class in _LOG_LEVEL_PATTERNS:
        html = pattern.sub(
            lambda m: (
                m.group(0)
                if "<span class=" in m.group(0)
                else f"<span class='{css_class}'>{m.group(1)}</span>"
            ),
            html,
        )
    return html


def escape_html(text: str) -> str:
    """Escape HTML special characters."""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#39;")
    )


def strip_ansi(text: str) -> str:
    """Strip ANSI escape codes from text."""
    ansi_escape = re.compile(r"\x1b\[([0-9;]+)m")
    return ansi_escape.sub("", text)


# EOF
