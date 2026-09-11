#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Positive control for the production-capture honesty gate.

WHY THIS FILE IS SEPARATE FROM THE CAPTURE, same reason as
``tests/develop/test_screenshot_session_role_guard.py``: the capture lives
under ``tests/e2e/`` and is skipped unless ``--browser`` is passed, so a guard
that only runs there is a guard nobody watches. These cases are pure functions
over strings and one YAML file, so they run in the ordinary pytest matrix on
every commit.

WHAT IT PROVES, in both directions, on every axis the guard has:

  * HTML WITHOUT a dev marker is accepted (otherwise the guard would reject
    every clean capture and be switched off);
  * HTML WITH the dev-only footer bar is rejected, naming it;
  * HTML WITH Vite dev-server asset URLs is rejected, naming them;
  * a run that DECLARES DEBUG=True is rejected even when the page looks clean —
    the leader's ruling is that a DEBUG capture may not satisfy production
    verification at all;
  * the marker list is tied to the REAL template, so renaming an id cannot
    silently empty the guard (an anti-vacuity control: a marker list that
    matched nothing would pass every page);
  * the ACCEPTANCE workflow declares the production switch, and the inert bare
    ``DEBUG`` variable is not relied on to turn debug off.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

from tests.e2e.playwright.capture_config_check import (
    DEBUG_ONLY_MARKERS,
    NotAProductionCaptureError,
    assert_capture_sequence,
    assert_production_capture,
    diagnose_capture_config,
    find_debug_only_markers,
    find_dev_server_asset_urls,
)

REPO = Path(__file__).resolve().parents[2]
FOOTER_TEMPLATE = REPO / "templates" / "global_base_partials" / "global_footer.html"
SCREENSHOTS_WORKFLOW = REPO / ".github" / "workflows" / "screenshots.yml"

WHERE = "Writer (/apps/writer/)"

#: A production-shaped page: the dev block is ABSENT (it is `{% if DEBUG %}`),
#: and assets come from the built, content-hashed manifest.
PRODUCTION_HTML = (
    '<html><body><div id="app-mount">'
    '<script src="/static/vite/console-interceptor-CEFINsk1.js"></script>'
    "</div></body></html>"
)

#: The same page as it renders under DEBUG: the dev-only footer bar present,
#: assets pointed at the host dev server.
DEBUG_HTML = (
    '<html><body><div id="app-mount">'
    '<script src="http://127.0.0.1:5173/shared/ts/utils/console-interceptor.ts"></script>'
    "</div>"
    '<div class="footer-dev-tools"><span class="dev-tools-label">Dev Tools:</span>'
    '<button id="init-visitor-pool-btn">Init Visitors</button></div>'
    "</body></html>"
)


class TestTheGuardAcceptsAProductionCapture:
    def test_production_html_is_accepted(self):
        assert_production_capture(PRODUCTION_HTML, where=WHERE)

    def test_production_html_has_no_reasons(self):
        assert diagnose_capture_config(PRODUCTION_HTML, where=WHERE) == []

    def test_clean_html_is_still_accepted_when_the_run_declares_production(self):
        assert_production_capture(PRODUCTION_HTML, where=WHERE, debug_declared=False)


class TestTheGuardRefusesADebugCapture:
    def test_the_dev_footer_bar_is_found(self):
        assert "footer-dev-tools" in find_debug_only_markers(DEBUG_HTML)

    def test_the_vite_dev_server_url_is_found(self):
        assert find_dev_server_asset_urls(DEBUG_HTML) == [
            ":5173/",
        ]

    def test_debug_html_is_refused(self):
        with pytest.raises(NotAProductionCaptureError) as excinfo:
            assert_production_capture(DEBUG_HTML, where=WHERE)
        assert "not evidence of the production configuration" in str(excinfo.value)

    def test_the_refusal_names_the_page(self):
        with pytest.raises(NotAProductionCaptureError) as excinfo:
            assert_production_capture(DEBUG_HTML, where=WHERE)
        assert WHERE in str(excinfo.value)

    def test_the_refusal_names_the_template_that_betrays_debug(self):
        with pytest.raises(NotAProductionCaptureError) as excinfo:
            assert_production_capture(DEBUG_HTML, where=WHERE)
        assert "global_footer.html" in str(excinfo.value)

    def test_a_declared_debug_run_is_refused_even_on_a_clean_page(self):
        # The leader's ruling: the DECLARATION is disqualifying on its own.
        with pytest.raises(NotAProductionCaptureError) as excinfo:
            assert_production_capture(PRODUCTION_HTML, where=WHERE, debug_declared=True)
        assert "declares DEBUG=True" in str(excinfo.value)

    def test_one_unfit_page_refuses_the_whole_run(self):
        with pytest.raises(NotAProductionCaptureError) as excinfo:
            assert_capture_sequence(
                [("Good (/apps/docs/)", PRODUCTION_HTML), (WHERE, DEBUG_HTML)]
            )
        assert WHERE in str(excinfo.value)

    def test_a_clean_run_passes_the_sequence_check(self):
        assert_capture_sequence(
            [("Docs (/apps/docs/)", PRODUCTION_HTML), (WHERE, PRODUCTION_HTML)]
        )


class TestTheMarkerListCannotSilentlyEmpty:
    """Anti-vacuity: markers must come from the template, not from memory."""

    def test_every_marker_still_exists_in_the_footer_template(self):
        template = FOOTER_TEMPLATE.read_text(encoding="utf-8")
        missing = [marker for marker in DEBUG_ONLY_MARKERS if marker not in template]
        assert missing == [], (
            f"{missing} are no longer in {FOOTER_TEMPLATE.name}, so the capture "
            "guard would accept a DEBUG page. Update DEBUG_ONLY_MARKERS with the "
            "renamed ids (and keep them inside the {% if DEBUG %} block)."
        )

    def test_the_marked_block_is_still_guarded_by_debug(self):
        template = FOOTER_TEMPLATE.read_text(encoding="utf-8")
        block_start = template.index("footer-dev-tools")
        before = template[:block_start]
        # The nearest conditional above the dev block must be `{% if DEBUG %}`.
        guards = re.findall(r"{%\s*if\s+([^%]+?)\s*%}", before)
        assert guards and guards[-1].strip() == "DEBUG", (
            "the dev-only footer block is no longer inside `{% if DEBUG %}` "
            f"(nearest guard above it: {guards[-1] if guards else None!r}). The "
            "capture guard keys on that block as proof of a DEBUG render; if it "
            "moved out of the conditional, the guard proves nothing."
        )


class TestTheAcceptanceWorkflowDeclaresProduction:
    """The declaration half, keyed to the workflow rather than the artifact."""

    @staticmethod
    def _steps() -> list[dict]:
        workflow = yaml.safe_load(SCREENSHOTS_WORKFLOW.read_text(encoding="utf-8"))
        jobs = workflow.get("jobs") or {}
        assert jobs, "screenshots.yml has no jobs"
        steps: list[dict] = []
        for job in jobs.values():
            steps.extend(job.get("steps") or [])
        assert steps, "screenshots.yml has no steps"
        return steps

    def test_the_server_that_is_photographed_runs_with_debug_off(self):
        env = self._env_of("Migrate & start server")
        assert env.get("SCITEX_HUB_DJANGO_DEBUG") == "0", (
            "the captured server does not export SCITEX_HUB_DJANGO_DEBUG=0. "
            "settings_dev.py:64 reads THAT name (default True); production "
            f"acceptance screenshots must be DEBUG=0. Env seen: {sorted(env)}"
        )

    def test_nothing_relies_on_the_inert_bare_debug_variable(self):
        for name in ("Migrate & start server", "Capture screenshots"):
            env = self._env_of(name)
            assert "DEBUG" not in env, (
                f"{name} still sets a bare `DEBUG` env var. It is INERT here: "
                "settings_dev.py:64 reads SCITEX_HUB_DJANGO_DEBUG, and the bare "
                "name is read only by settings_prod/staging. Leaving it makes a "
                "DEBUG capture look like a deliberate production setting."
            )

    def test_the_capture_still_runs_its_own_visual_and_security_checks(self):
        # Preserving the existing gates is part of the card's brief; this pins
        # it so a future speed-up cannot quietly drop them while flipping DEBUG.
        #
        # NOTE ON WHAT IS *NOT* ASSERTED HERE. My first version of this test
        # looked for the literal "assert_pooled_visitor" in the workflow and
        # failed: that assertion lives in tests/e2e/playwright/conftest.py's
        # fixture, not in the workflow text. The workflow's contract is the
        # COMMAND, so the command is what is pinned — and the modules named in
        # it are the ones that carry the content assertions, the pooled-visitor
        # check and the content-check positive control.
        run = self._run_of("Capture screenshots")
        for marker in (
            "--browser chromium",
            "tests/e2e/playwright/test_capture_screenshots.py",
            "tests/e2e/playwright/test_content_check_fires.py",
            "--timeout=120",
        ):
            assert marker in run, (
                f"{marker!r} is no longer part of the capture command. The "
                "DEBUG flip must not remove the visual, content or session "
                "checks that make the artifact trustworthy."
            )

    def test_the_debug_off_capture_declares_an_email_backend(self):
        """DEBUG=0 turns the operator mail rail ON, so a backend must be named.

        MEASURED on this PR's first run (job 103097274649, 2026-09-11). With
        DEBUG=1 Django's ``require_debug_false`` filter kept ``mail_admins``
        silent; with DEBUG=0 the first ERROR log reached AdminEmailHandler,
        settings_shared.py:442 defaults EMAIL_BACKEND to None when
        SCITEX_HUB_EMAIL_BACKEND is unset, and ``import_string(None)`` raised

            AttributeError: 'NoneType' object has no attribute 'rsplit'

        which failed the "Migrate & start server" step before a single page was
        captured. The environment must satisfy what DEBUG=0 requires; this pins
        that so the same crash cannot return unnoticed.
        """
        for name in ("Migrate & start server", "Capture screenshots"):
            env = self._env_of(name)
            assert env.get("SCITEX_HUB_EMAIL_BACKEND"), (
                f"{name} runs with DEBUG=0 but declares no "
                "SCITEX_HUB_EMAIL_BACKEND. At DEBUG=0 the operator mail rail is "
                "live and settings_shared.py:442 leaves EMAIL_BACKEND None, so "
                "the first ERROR log becomes an AttributeError that kills the "
                f"step. Env seen: {sorted(env)}"
            )

    def test_the_debug_off_capture_builds_the_static_root(self):
        """DEBUG=0 serves static from STATIC_ROOT, so it must be built.

        MEASURED on this PR's second run (job 103099211496, 2026-09-11): the
        capture RAN and failed with 21 browser errors, every one

            Refused to apply style from /static/public_app/css/landing/*.css
            because its MIME type ('text/html') is not a supported stylesheet
            MIME type

        — the CSS URLs answered HTML, because the DEBUG=1 finder path is gone at
        DEBUG=0, WhiteNoise falls back to STATIC_ROOT, and nothing had run
        collectstatic. Second instance of the same shape (the first was the
        operator mail rail needing an EMAIL_BACKEND): production-mode removes
        something DEBUG was supplying implicitly.
        """
        run = self._run_of("Migrate & start server")
        assert "collectstatic" in run, (
            "the DEBUG=0 capture never builds STATIC_ROOT, so every app "
            "stylesheet 404s into the catch-all and returns HTML under a "
            f".css URL. Add collectstatic before the server starts:\n{run[:400]}"
        )

    @classmethod
    def _env_of(cls, fragment: str) -> dict:
        for step in cls._steps():
            if fragment.lower() in str(step.get("name", "")).lower():
                return dict(step.get("env") or {})
        raise AssertionError(f"no step named like {fragment!r} in screenshots.yml")

    @classmethod
    def _run_of(cls, fragment: str) -> str:
        for step in cls._steps():
            if fragment.lower() in str(step.get("name", "")).lower():
                return str(step.get("run") or "")
        raise AssertionError(f"no step named like {fragment!r} in screenshots.yml")
