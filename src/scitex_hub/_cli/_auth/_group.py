#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Top-level ``auth`` Click group.

Lives in its own module so verb modules can import the singleton
without import cycles, mirroring the ``_account/_group.py`` pattern.
The console singleton is reused for consistent rich-rendering.
"""

from __future__ import annotations

import click
from rich.console import Console

from .._click_compat import spec_group_kwargs

console = Console()


@click.group(
    **spec_group_kwargs(
        summary="Browser-free credential operations (login: mint + cache a PAT)."
    )
)
def auth() -> None:
    """Browser-free credential operations (login → mint+cache PAT)."""


__all__ = ["auth", "console"]

# EOF
