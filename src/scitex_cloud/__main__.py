#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: src/scitex_cloud/__main__.py
"""``python -m scitex_cloud`` — point at the renamed entry point.

``scitex_cloud`` is the legacy distribution / module name of
``scitex_hub`` (see ``docs/adr/0001-rename-scitex-cloud-to-scitex-hub.md``).
Importing the package already emits a ``DeprecationWarning`` and re-exports
``scitex_hub``; running it as a module here forwards execution to
``scitex_hub.__main__`` with the same warning, so legacy invocations of

    $ python -m scitex_cloud --help

continue to work while operators migrate to the canonical

    $ python -m scitex_hub --help

The shim and this forwarder will be removed in a future major release.
"""

from __future__ import annotations

import runpy
import warnings

warnings.warn(
    "`python -m scitex_cloud` is a deprecated alias of "
    "`python -m scitex_hub` (the package was renamed in v0.18.0; see "
    "docs/adr/0001-rename-scitex-cloud-to-scitex-hub.md). Update your "
    "invocation; this forwarder will be removed in a future major release.",
    DeprecationWarning,
    stacklevel=2,
)

runpy.run_module("scitex_hub", run_name="__main__", alter_sys=True)
