#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: tests/apps/scholar_app/conftest.py
"""Scholar cutover fixtures (CCT 2760 + CCT 2763/2764 + CCT 2806).

/apps/scholar/ serves the LEAF now; the pre-cutover hub-native routes live
ONLY at /apps/scholar/old-direct/ in dev (dev-gated, never in production).
DB-backed tests that drive those hub views through the Django test client
need the gate ON for the duration of the test: the client resolves per
request through Django's cached root urlconf, which is built at import time
with the gate off (the suite runs prod-shaped, DEBUG False).

``scholar_old_direct`` turns the gate on around ONE test — reload the REAL
root urlconf with the explicit flag, clear the cached resolver so the
client sees the fresh patterns, then restore (reload + clear) AFTER the
override exits. Restoring inside the flag window would re-mount old-direct
and leak the gate into the suite's ambient urlconf.

Opt-in per test (NOT autouse): most scholar tests assert about the LEAF or
about the user path, and must see the ambient prod-shaped urlconf.
"""

from __future__ import annotations

import pytest


@pytest.fixture
def scholar_old_direct():
    """Serve the old-direct parity reference to the Django test client."""
    import importlib

    import config.urls as root_urlconf
    from django.test.utils import override_settings
    from django.urls import clear_url_caches

    gate = override_settings(SCHOLAR_OLD_DIRECT_ENABLED=True)
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
