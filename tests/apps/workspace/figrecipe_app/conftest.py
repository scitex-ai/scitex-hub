#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: tests/apps/workspace/figrecipe_app/conftest.py
"""FigRecipe cutover fixtures (CCT-2784 + CCT 2763/2764 + CCT 2806).

/apps/figrecipe/ serves the LEAF now; the pre-cutover hub-native routes live
ONLY at /apps/figrecipe/old-direct/ in dev (dev-gated, never in production).
DB-backed tests that drive those hub views through the Django test client
need the gate ON for the duration of the test: the client resolves per
request through Django's cached root urlconf, which is built at import time
with the gate off (the suite runs prod-shaped, DEBUG False).

``figrecipe_old_direct`` turns the gate on around ONE test — reload the REAL
root urlconf with the explicit flag, clear the cached resolver so the
client sees the fresh patterns, then restore (reload + clear) AFTER the
override exits. Restoring inside the flag window would re-mount old-direct
and leak the gate into the suite's ambient urlconf.

Opt-in per test (NOT autouse): most figrecipe tests assert about the LEAF or
about the user path, and must see the ambient prod-shaped urlconf.
"""

from __future__ import annotations

import pytest


@pytest.fixture
def figrecipe_old_direct():
    """Serve the old-direct parity reference to the Django test client."""
    import importlib

    import config.urls as root_urlconf
    from django.test.utils import override_settings
    from django.urls import clear_url_caches

    gate = override_settings(FIGRECIPE_OLD_DIRECT_ENABLED=True)
    gate.enable()
    try:
        importlib.reload(root_urlconf)
        clear_url_caches()
        yield
    finally:
        gate.disable()
        importlib.reload(root_urlconf)
        clear_url_caches()


# EOF
