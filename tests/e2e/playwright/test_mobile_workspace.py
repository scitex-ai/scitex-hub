#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Mobile Workspace Tests

Verify the workspace default pane behavior on mobile viewport.
"""

import pytest
from tests.e2e.playwright.page_ready import wait_for_page_ready
from tests.e2e.playwright.conftest import TIMEOUT


def _chat_pane_dom_evidence(page) -> str:
    """Full DOM evidence for the chat-pane contract, for failure diagnosis.

    Captures the id/classes/computed visibility/bounding box of #pane-chat and
    its inner surface, the active pane, and body[data-initial-pane]. Read
    without raising -- this runs inside the failure path and must never mask
    the original error.
    """
    try:
        return page.evaluate(
            """
            () => {
                const info = (el) => {
                    if (!el) return null;
                    const r = el.getBoundingClientRect();
                    const cs = getComputedStyle(el);
                    return {
                        id: el.id || null,
                        classes: el.className || null,
                        display: cs.display,
                        visibility: cs.visibility,
                        opacity: cs.opacity,
                        box: { x: Math.round(r.x), y: Math.round(r.y),
                                w: Math.round(r.width), h: Math.round(r.height) },
                    };
                };
                return JSON.stringify({
                    url: location.href,
                    data_initial_pane: document.body.getAttribute('data-initial-pane'),
                    data_session_role: document.body.getAttribute('data-session-role'),
                    active_pane: info(document.querySelector('.workspace-pane.active')),
                    pane_chat: info(document.querySelector('#pane-chat')),
                    chat_surface: info(
                        document.querySelector('#pane-chat .ws-ai-pane')
                        || document.querySelector('#pane-chat #stx-shell-ai-panel')
                    ),
                    all_panes: Array.from(document.querySelectorAll('.workspace-pane'))
                        .map(info),
                }, null, 2);
            }
        """
        )
    except Exception as exc:  # noqa: BLE001 -- evidence must not mask the error
        return f"<could not read DOM evidence: {exc}>"


# WHY THESE TESTS DO NOT WAIT FOR `networkidle`
#
# `networkidle` means "500 ms with zero requests in flight". A SciTeX page
# held by a pooled visitor session runs a heartbeat/countdown poller for as
# long as the page is open (PoolAllocator.extend_session_on_activity), so
# that condition never arrives and the wait always times out. The page is
# fine; the question is unanswerable.
#
# Measured twice, same exception both times:
#   2026-08-16, CI run 31955719803 -- 30s timeout, 33 errors, capture down.
#   2026-09-06, job 101449817274   -- 30s timeout, 14/14 mobile tests
#                                     ERRORED in fixture setup, so not one
#                                     assertion in the mobile suite had
#                                     ever been evaluated.
#
# `wait_for_page_ready` (load -> body.app-ready -> short settle) was written
# after the first of those and is the sanctioned wait. See
# tests/e2e/playwright/page_ready.py for why each step is there and why none
# of them can hide a broken page.


class TestMobileWorkspace:
    """Workspace module on iPhone 14 viewport."""

    def test_workspace_page_loads(self, visitor_mobile_page, screenshot):
        """Workspace page loads on mobile (canonical /chat/ route)."""
        resp = visitor_mobile_page.goto("/chat/")
        screenshot(visitor_mobile_page, "workspace_mobile_loaded")
        assert resp.status == 200, f"Workspace page returned {resp.status}"

    def test_workspace_default_pane_visible(self, visitor_mobile_page, screenshot):
        """Workspace shows the default (chat) pane on mobile load at /chat/.

        /apps/workspace/ (module="chat") redirects to the canonical /chat/
        route. The default pane there is #pane-chat, rendered active and
        visible in the unified workspace layout.
        """
        visitor_mobile_page.goto("/chat/")
        wait_for_page_ready(visitor_mobile_page)

        # The canonical active pane at /chat/ is #pane-chat.
        try:
            visitor_mobile_page.wait_for_selector(
                "#pane-chat.workspace-pane.active", timeout=TIMEOUT
            )
        except Exception as exc:  # noqa: BLE001
            screenshot(visitor_mobile_page, "workspace_default_pane_FAILED")
            raise AssertionError(
                "#pane-chat did not become the active pane at /chat/ within "
                f"{TIMEOUT}ms.\nDOM evidence:\n{_chat_pane_dom_evidence(visitor_mobile_page)}\n({exc})"
            ) from exc

        pane = visitor_mobile_page.locator("#pane-chat.workspace-pane.active")
        assert pane.is_visible(), (
            "Default chat pane is not visible on mobile. "
            f"DOM evidence:\n{_chat_pane_dom_evidence(visitor_mobile_page)}"
        )
        screenshot(visitor_mobile_page, "workspace_default_pane")

    def test_workspace_default_module_is_chat(self, visitor_mobile_page, screenshot):
        """Default module is the ACTIVE, VISIBLE chat pane on /chat/.

        The legacy 3-pane robot-icon chat shell was retired: /apps/workspace/
        (module="chat") redirects to the canonical /chat/ route, where chat is
        the active pane in the unified workspace layout (workspace_app/views.py
        and global_base.html -- #pane-chat is server-rendered with the "active"
        class and body[data-initial-pane="chat"] when request.initial_pane is
        "chat").

        The assertion targets the CANONICAL #pane-chat element specifically --
        not a broad .workspace-pane.active union, whose first DOM match can be
        the hidden #pane-module, which is how this test once read the wrong
        pane. It also proves the chat surface is VISIBLE (non-zero bounding
        box), and on failure captures full DOM evidence (id, classes, computed
        display/visibility/opacity, bounding boxes, data-initial-pane, and a
        screenshot) so a timing/contract regression is diagnosable from the
        artifact rather than a bare "None".
        """
        visitor_mobile_page.goto("/chat/")
        wait_for_page_ready(visitor_mobile_page)

        # Wait for the canonical chat pane to exist and be the active pane,
        # then for its inner surface to have real layout. This is the timing
        # the previous test skipped: it read the DOM before the chat pane was
        # activated, so it caught the hidden module pane.
        try:
            visitor_mobile_page.wait_for_selector(
                "#pane-chat.workspace-pane.active", timeout=TIMEOUT
            )
            # The visible chat surface on mobile is the inner AI panel; wait
            # for it to be laid out (non-zero box) rather than just present.
            visitor_mobile_page.wait_for_function(
                """() => {
                    const el = document.querySelector('#pane-chat .ws-ai-pane')
                        || document.querySelector('#pane-chat #stx-shell-ai-panel')
                        || document.querySelector('#pane-chat');
                    if (!el) return false;
                    const r = el.getBoundingClientRect();
                    return r.width > 0 && r.height > 0;
                }""",
                timeout=TIMEOUT,
            )
        except Exception as exc:  # noqa: BLE001 -- re-raised with DOM evidence
            evidence = _chat_pane_dom_evidence(visitor_mobile_page)
            screenshot(visitor_mobile_page, "workspace_default_module_FAILED")
            raise AssertionError(
                "chat pane did not become the active, visible pane at /chat/ "
                f"within {TIMEOUT}ms.\nDOM evidence:\n{evidence}\n({exc})"
            ) from exc

        active_module = visitor_mobile_page.evaluate(
            """
            () => {
                // Canonical: the active pane's data-pane.
                const activePane = document.querySelector(
                    '.workspace-pane.active[data-pane]'
                );
                if (activePane) return activePane.getAttribute('data-pane');
                // Fallback: the body's initial-pane marker set by /chat/.
                return document.body.getAttribute('data-initial-pane');
            }
        """
        )
        # Prove the chat pane is the active one AND its surface is visible.
        pane_visible = visitor_mobile_page.evaluate(
            """
            () => {
                const el = document.querySelector('#pane-chat .ws-ai-pane')
                    || document.querySelector('#pane-chat #stx-shell-ai-panel')
                    || document.querySelector('#pane-chat');
                if (!el) return false;
                const r = el.getBoundingClientRect();
                const cs = getComputedStyle(el);
                return r.width > 0 && r.height > 0
                    && cs.display !== 'none' && cs.visibility !== 'hidden';
            }
        """
        )
        screenshot(visitor_mobile_page, "workspace_default_module")
        assert active_module == "chat", (
            f"Expected the active pane to be 'chat', got '{active_module}'. "
            f"DOM evidence:\n{_chat_pane_dom_evidence(visitor_mobile_page)}"
        )
        assert pane_visible, (
            "The active chat pane is not visibly rendered (zero box or "
            f"hidden). DOM evidence:\n{_chat_pane_dom_evidence(visitor_mobile_page)}"
        )

    def test_workspace_no_horizontal_overflow(self, visitor_mobile_page):
        """Workspace does not overflow horizontally on mobile at /chat/."""
        visitor_mobile_page.goto("/chat/")
        wait_for_page_ready(visitor_mobile_page)

        overflow = visitor_mobile_page.evaluate(
            """
            () => {
                return document.documentElement.scrollWidth > document.documentElement.clientWidth;
            }
        """
        )
        assert (
            not overflow
        ), "Workspace has horizontal overflow on mobile viewport (390px)"

    def test_workspace_pane_fills_viewport(self, visitor_mobile_page):
        """Default pane fills most of the mobile viewport width at /chat/."""
        visitor_mobile_page.goto("/chat/")
        wait_for_page_ready(visitor_mobile_page)

        # Canonical active pane at /chat/ is #pane-chat (not a broad union,
        # whose first match can be a hidden pane and give a misleading box).
        try:
            visitor_mobile_page.wait_for_selector(
                "#pane-chat.workspace-pane.active", timeout=TIMEOUT
            )
        except Exception as exc:  # noqa: BLE001
            raise AssertionError(
                "#pane-chat did not become the active pane at /chat/ within "
                f"{TIMEOUT}ms.\nDOM evidence:\n{_chat_pane_dom_evidence(visitor_mobile_page)}\n({exc})"
            ) from exc

        pane = visitor_mobile_page.locator("#pane-chat.workspace-pane.active")
        box = pane.bounding_box()
        if box is None:
            pytest.skip("Workspace pane not visible")

        viewport = visitor_mobile_page.viewport_size
        # Pane should use at least 80% of viewport width on mobile
        assert box["width"] >= viewport["width"] * 0.8, (
            f"Pane width {box['width']}px is less than 80% of "
            f"viewport width {viewport['width']}px"
        )
