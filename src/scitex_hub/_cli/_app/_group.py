#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Top-level ``app`` Click group.

Pulled into its own module so verb modules can import the singleton without
creating import cycles. The console singleton is reused throughout the
subpackage to keep rich-rendering consistent.
"""

from __future__ import annotations

import click
from rich.console import Console

from .._click_compat import spec_group_kwargs

console = Console()


@click.group(**spec_group_kwargs(summary="Manage SciTeX app plugins."))
def app() -> None:
    """Manage SciTeX app plugins."""


__all__ = ["app", "console"]

# EOF
