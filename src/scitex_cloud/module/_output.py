#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Thread-local output collection for SciTeX module execution."""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import Any


class _SafeHtml:
    """Wrapper marking a string as pre-sanitized HTML.

    The renderer will emit this content as-is without escaping.
    """

    def __init__(self, content: str):
        self._content = str(content)

    @property
    def content(self) -> str:
        return self._content

    def __str__(self) -> str:
        return self._content

    def __repr__(self) -> str:
        truncated = (
            self._content[:60] + "..." if len(self._content) > 60 else self._content
        )
        return f"_SafeHtml({truncated!r})"


_OUTPUT_TYPE_AUTO = ""


@dataclass
class ModuleOutput:
    """Single output item produced by a module function."""

    value: Any = None
    title: str = ""
    output_type: str = field(default=_OUTPUT_TYPE_AUTO)

    def __post_init__(self):
        if self.output_type == _OUTPUT_TYPE_AUTO:
            self.output_type = _detect_type(self.value)


def _detect_type(value: Any) -> str:
    """Infer a human-readable output type from value."""
    if isinstance(value, _SafeHtml):
        return "html"

    type_name = type(value).__name__
    module_name = type(value).__module__ or ""
    if "matplotlib" in module_name and type_name == "Figure":
        return "figure"

    if "pandas" in module_name and type_name == "DataFrame":
        return "table"

    if isinstance(value, dict):
        return "json"

    if isinstance(value, str):
        return "text"

    return "text"


class ModuleOutputCollector:
    """Thread-local collector that accumulates outputs during module execution."""

    _local = threading.local()

    @classmethod
    def get_current(cls) -> list[ModuleOutput]:
        """Return the output list for the current thread."""
        if not hasattr(cls._local, "outputs"):
            cls._local.outputs = []
        return list(cls._local.outputs)

    @classmethod
    def add(cls, value: Any, title: str = "") -> None:
        """Append an output item for the current thread."""
        if not hasattr(cls._local, "outputs"):
            cls._local.outputs = []
        cls._local.outputs.append(ModuleOutput(value=value, title=title))

    @classmethod
    def clear(cls) -> None:
        """Discard all collected outputs for the current thread."""
        cls._local.outputs = []


def output(value: Any, title: str = "") -> None:
    """Add an output to the current module execution.

    This is the primary API researchers call inside their module function
    to register figures, tables, text, or HTML for display.
    """
    ModuleOutputCollector.add(value, title)


def html(content: str) -> _SafeHtml:
    """Mark a string as safe HTML so the renderer emits it without escaping."""
    return _SafeHtml(content)


# EOF
