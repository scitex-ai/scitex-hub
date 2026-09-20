#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Top-level ``account`` Click group.

Pulled into its own module so verb modules can import the singleton
without creating import cycles. The console singleton is reused
throughout the subpackage for consistent rich-rendering.
"""

from __future__ import annotations

import click

from scitex_hub._logging import get_console

console = get_console(__name__)


@click.group()
def account() -> None:
    """Manage your SciTeX Hub account (tokens, identity, health)."""


@account.group("token")
def token() -> None:
    """Create, list, and revoke API tokens for the CLI."""


__all__ = ["account", "console", "token"]

# EOF
