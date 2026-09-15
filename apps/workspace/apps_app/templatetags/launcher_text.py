#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Line-break hints for launcher tile names."""

import re

from django import template
from django.utils.html import escape
from django.utils.safestring import mark_safe

register = template.Library()

# Tile names wrap with `word-break: keep-all` (grid.css), which forbids breaks
# inside a katakana run; <wbr> marks where a long compound may split instead.
_KATAKANA_COMPOUND_JOIN = re.compile(r"(?<=[゠-ヿ])(?=プロジェクト|ストア)")


@register.filter
def phrase_breaks(name) -> str:
    """Escape ``name`` and allow a line break between katakana compound words."""
    return mark_safe(_KATAKANA_COMPOUND_JOIN.sub("<wbr>", escape(name)))
