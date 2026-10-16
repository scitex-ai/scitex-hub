#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Dev-gate helper for Writer old-direct tests (cutover + CCT 2763/2764).

/apps/writer/ serves the LEAF now; the pre-cutover hub-native routes live
ONLY at /apps/writer/old-direct/ in dev (dev-gated, never in production).
DB-backed tests that drive those hub views through the Django test client
need the gate ON for the duration of the test: the client resolves per
request through Django's cached root urlconf, which is built at import time
with the gate off (the suite runs prod-shaped, DEBUG False).

Two entry points, one definition:

* ``writer_old_direct_urls()`` — context manager for Django ``TestCase``
  classes, where fixture-as-argument injection does not apply (``with``
  blocks around the client drive are framework-proof — same reload +
  clear_url_caches pattern as the figrecipe/scholar helpers).
* ``writer_old_direct`` — pytest fixture (opt-in per test, NOT autouse:
  most writer tests assert about the LEAF or the user path and must see
  the ambient prod-shaped urlconf).

Both reload the REAL root urlconf with the explicit flag, clear the cached
resolver so the client sees the fresh patterns, then restore (reload +
clear) AFTER the override exits. Restoring inside the flag window would
re-mount old-direct and leak the gate into the suite's ambient urlconf.
"""

from __future__ import annotations

import contextlib
import importlib

import pytest
from django.test.utils import override_settings
from django.urls import clear_url_caches

WRITER_OLD_DIRECT_FLAG = "WRITER_OLD_DIRECT_ENABLED"


@contextlib.contextmanager
def writer_old_direct_urls():
    """Serve the old-direct parity reference to the Django test client."""
    gate = override_settings(**{WRITER_OLD_DIRECT_FLAG: True})
    gate.enable()
    try:
        import config.urls as root_urlconf

        importlib.reload(root_urlconf)
        clear_url_caches()
        yield
    finally:
        gate.disable()
        importlib.reload(root_urlconf)
        clear_url_caches()


@pytest.fixture
def writer_old_direct():
    """Pytest fixture form of :func:`writer_old_direct_urls`."""
    with writer_old_direct_urls():
        yield


# EOF
