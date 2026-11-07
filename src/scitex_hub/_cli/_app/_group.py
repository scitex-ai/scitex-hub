#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Top-level ``app`` Click group.

Pulled into its own module so verb modules can import the singleton without
creating import cycles. The console singleton is reused throughout the
subpackage to keep rich-rendering consistent.
"""

from __future__ import annotations

import click

from scitex_hub._logging import get_console

console = get_console(__name__)


@click.group()
def app() -> None:
    """Manage SciTeX app plugins."""


__all__ = ["app", "console"]

# EOF
