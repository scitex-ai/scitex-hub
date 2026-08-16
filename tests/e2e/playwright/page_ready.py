#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""When is a SciTeX page finished enough to read or photograph?

WHY NOT ``networkidle``. It is the obvious answer and it is wrong for this
product. ``networkidle`` waits for 500 ms with no in-flight requests, and a
SciTeX page held by a POOLED VISITOR never has that: the visitor session
runs a heartbeat/countdown poller (the same one that promotes the 2-minute
probation lease to a full session — ``PoolAllocator.extend_session_on_activity``),
so requests keep arriving forever. Measured in CI on 2026-08-16, run
31955719803: ``wait_for_load_state("networkidle")`` on ``/apps/home/`` threw
``TimeoutError: Timeout 30000ms exceeded`` and took the whole capture down
with 33 errors. Nothing was broken about the page — the wait condition was
simply one this page can never satisfy.

WHAT IS USED INSTEAD, in order:

1. ``load`` — subresources are in. Fires regardless of ongoing XHR, so a
   live poller cannot stall it.
2. ``body.app-ready`` — the product's OWN hydration signal, added by
   ``main.ts initApp()`` and guaranteed within 3 s by the safety-net script
   in ``templates/global_base.html`` even when the Vite bundle fails. This
   is a REAL gate: it raises if the page never becomes ready, which is
   exactly the "photographed an empty shell" failure the capture cares
   about. ``tests/e2e/playwright/conftest.py``'s login fixture already
   waits on this same class for the same reason.
3. A short fixed settle, for renders that paint just after hydration.
   Measured 2026-08-16: reading a page mid-hydration produced four false
   "this is broken" reports in one session.

No step here swallows a failure. Step 2 is the loud one; steps 1 and 3
cannot fail in a way that hides a broken page, and the caller's own
assertions (HTTP status, session role, non-blank body text) still run
afterwards.
"""

from __future__ import annotations

import os

#: How long to wait for the product's hydration signal before failing.
APP_READY_TIMEOUT_MS = int(os.getenv("SCITEX_E2E_APP_READY_MS", "15000"))

#: Quiet time after hydration, for anything that paints a beat later.
SETTLE_MS = int(os.getenv("SCITEX_E2E_SETTLE_MS", "1500"))

APP_READY_JS = (
    "() => !!(document.body && document.body.classList.contains('app-ready'))"
)


def wait_for_page_ready(page, *, hydration_signal: bool = True) -> None:
    """Block until ``page`` is hydrated and settled enough to be read.

    Args:
        page: the Playwright page.
        hydration_signal: whether this page emits ``body.app-ready``. Pass
            ``False`` ONLY for a route whose response does not extend
            ``templates/global_base.html`` — the class is emitted by that
            template, so waiting for it on a standalone page waits for
            something that will never arrive. The caller must name such
            routes in one declared place (see
            ``test_capture_screenshots.ROUTES_WITHOUT_GLOBAL_BASE``), never
            decide per call site, because "this page is different" is how a
            check quietly becomes optional everywhere.

    Raises:
        playwright TimeoutError: if a global_base page never reaches
            ``app-ready``. That is a genuine failure — the page did not
            finish booting — and it must stop the capture rather than yield
            a PNG of a loading spinner.
    """
    page.wait_for_load_state("load")
    if hydration_signal:
        page.wait_for_function(APP_READY_JS, timeout=APP_READY_TIMEOUT_MS)
    page.wait_for_timeout(SETTLE_MS)


# EOF
