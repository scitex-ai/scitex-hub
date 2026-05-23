#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SciTeX Cloud Module -- decorator and output APIs for custom workspace modules.

Usage:
    from scitex_hub.module import module, output, html, INJECTED

    @module(label="My Analysis", icon="fa-brain", category="analysis")
    def my_analysis(project=INJECTED, plt=INJECTED):
        output(df, title="Raw Data")
"""

from __future__ import annotations


# Sentinel object for decorator-injected parameters
class _InjectedSentinel:
    """Sentinel value indicating a parameter will be injected by the module runner."""

    def __repr__(self):
        return "<INJECTED>"


INJECTED = _InjectedSentinel()

from ._decorator import module
from ._manifest import ModuleManifest
from ._output import ModuleOutput, ModuleOutputCollector, html, output
from ._renderer import render_output, render_outputs

__all__ = [
    "INJECTED",
    "module",
    "ModuleManifest",
    "ModuleOutput",
    "ModuleOutputCollector",
    "output",
    "html",
    "render_output",
    "render_outputs",
]

# EOF
