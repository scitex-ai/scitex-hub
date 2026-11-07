#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""When is a SciTeX page finished enough to read or photograph?

WHY NOT ``networkidle``. It is the obvious answer and it is wrong for this
product. ``networkidle`` waits for 500 ms with no in-flight requests, and a
SciTeX page held by a SYNTHETIC REGISTERED USER never has that: the authenticated session
runs a heartbeat/countdown poller (the same one that promotes the 2-minute
probation lease to a full session — ``PoolAllocator.extend_session_on_activity``),
so requests keep arriving forever. Measured in CI on 2026-08-16, run
31955719803: ``wait_for_load_state("networkidle")`` on ``/apps/my-projects/`` threw
``TimeoutError: Timeout 30000ms exceeded`` and took the whole capture down
with 33 errors. Nothing was broken about the page — the wait condition was
simply one this page can never satisfy.

WHAT IS USED INSTEAD, in order:

1. ``load`` for ordinary callers. Screenshot capture deliberately skips this:
   it starts its hard checks after the main response is committed, because a
   large or stalled subresource graph is not product readiness.
2. The owning shell's hydration signal. Hub global pages use
   ``body.app-ready``, added by
   ``main.ts initApp()`` and guaranteed within 3 s by the safety-net script
   in ``templates/global_base.html`` even when the Vite bundle fails. This
   is a REAL gate: it raises if the page never becomes ready, which is
   exactly the "photographed an empty shell" failure the capture cares
   about. ``tests/e2e/playwright/conftest.py``'s login fixture already
   waits on this same class for the same reason.
   SDK standalone pages instead require their direct SDK shell, a visible
   nonempty module and the actual SDK JavaScript-mounted app header. A missing
   bundle or an empty shell cannot satisfy that branch.
3. A short fixed settle, for renders that paint just after hydration.
   Measured 2026-08-16: reading a page mid-hydration produced four false
   "this is broken" reports in one session.

No step here swallows a failure. Step 2 is the loud one; screenshot callers
also retain their HTTP status, session-role, rendered-content, and image
assertions before accepting the page.
"""

from __future__ import annotations

import os

#: How long to wait for the product's hydration signal before failing.
APP_READY_TIMEOUT_MS = int(os.getenv("SCITEX_E2E_APP_READY_MS", "15000"))

#: Quiet time after hydration, for anything that paints a beat later.
SETTLE_MS = int(os.getenv("SCITEX_E2E_SETTLE_MS", "1500"))

APP_READY_JS = """() => {
    if (document.body?.classList.contains('app-ready')) return true;
    // SDK standalone owns this direct root, not global_base's lifecycle.
    const shell = document.querySelector('body > #workspace-three-col');
    if (!shell) return false;
    const module = shell.querySelector('.ws-module-pane');
    const header = shell.querySelector('[data-stx-app-header][data-stx-app-header-mounted]');
    if (!module || !header || !module.getClientRects().length || !header.getClientRects().length) return false;
    const content = (module.innerText || '').replace(header.innerText || '', '').trim();
    return content.length > 0;
}"""


def wait_for_page_ready(
    page, *, hydration_signal: bool = True, wait_for_load: bool = True
) -> None:
    """Block until ``page`` is hydrated and settled enough to be read.

    Args:
        page: the Playwright page.
        hydration_signal: require the owning Hub or SDK shell's in-band
            readiness signal. False is reserved for explicitly declared
            responses with neither shell (for example a restricted placeholder
            in test_capture_screenshots.ROUTES_WITHOUT_HYDRATION). Native SDK
            pages use the default True; they require the mounted header and
            visible module content rather than skipping readiness.
        wait_for_load: whether to wait for the browser's global ``load`` event.
            Screenshot capture passes ``False`` because it separately requires
            the product hydration signal and checks rendered content and images;
            an unrelated slow subresource must not block those checks.

    Raises:
        playwright TimeoutError: if the owning shell never becomes ready. That is a genuine failure — the page did not
            finish booting — and it must stop the capture rather than yield
            a PNG of a loading spinner.
    """
    if wait_for_load:
        page.wait_for_load_state("load")
    if hydration_signal:
        page.wait_for_function(APP_READY_JS, timeout=APP_READY_TIMEOUT_MS)
    elif not wait_for_load:
        page.wait_for_selector("body", state="attached", timeout=APP_READY_TIMEOUT_MS)
    page.wait_for_timeout(SETTLE_MS)


# EOF
