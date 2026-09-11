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

import os
import re
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from tests.e2e.playwright.capture_config_check import (
    DEBUG_ONLY_MARKERS,
    KNOWN_BASE_BROWSER_PROBLEMS,
    NotAProductionCaptureError,
    assert_capture_sequence,
    assert_no_unowned_browser_problems,
    assert_production_capture,
    classify_browser_problems,
    diagnose_capture_config,
    KNOWN_BASE_BROWSER_PROBLEMS,
    find_debug_only_markers,
    find_dev_server_asset_urls,
)
from tests.e2e.playwright.content_check import BrowserProblemLog

#: The CI-only values the screenshots job exports (see .github/workflows/
#: screenshots.yml). Explicit, not inherited: the probe child must load the
#: capture settings the way the job does, not the way this shell happens to.
CHILD_ENV = {
    "SCITEX_HUB_DJANGO_SECRET_KEY": "ci-test-secret-do-not-use-in-prod",  # pragma: allowlist secret
    "SCITEX_HUB_DB_NAME_DEV": "scitex_test",
    "SCITEX_HUB_DB_USER_DEV": "scitex",
    "SCITEX_HUB_DB_PASSWORD_DEV": "scitex_test_pass",  # pragma: allowlist secret
    "SCITEX_HUB_DB_HOST_DEV": "localhost",
    "SCITEX_HUB_DB_PORT_DEV": "5432",
    "SCITEX_HUB_GITEA_SSH_PORT_DEV": "2222",
    "SCITEX_HUB_VITE_USE_BUILD": "1",
}

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

    def test_a_console_echo_of_a_carded_problem_is_allowed_on_that_page(self):
        """The browser log records ONE failure TWICE.

        A structured line carrying the URL, and a URL-less console echo. The
        allowlist can only match the first by URL, so without this rule an
        already-carded problem is refused because of its own echo — which is exactly
        what made the capture red on a run where every problem was carded.
        """
        # Arrange
        problems = [
            "HTTP 404 http://127.0.0.1:8000/media/videos/scitex-automated-research-demo.mp4",
            "console.error: Failed to load resource: the server responded with a "
            "status of 404 (Not Found)",
        ]

        # Act
        hard, allowed = classify_browser_problems(problems)

        # Assert
        assert hard == []
        assert len(allowed) == 2

    def test_a_console_echo_does_not_excuse_a_status_that_is_not_carded_on_that_page(
        self,
    ):
        """THE CONTROL. Without this, the echo rule is a blanket 404 amnesty and the
        gate stops catching the thing it exists to catch."""
        # Arrange — the page has a carded 404, and a NEW 500.
        problems = [
            "HTTP 404 http://127.0.0.1:8000/media/videos/scitex-automated-research-demo.mp4",
            "console.error: Failed to load resource: the server responded with a "
            "status of 500 (Internal Server Error)",
        ]

        # Act
        hard, allowed = classify_browser_problems(problems)

        # Assert — the 404 echo is excused, the 500 is NOT.
        assert len(hard) == 1
        assert "500" in hard[0]
        assert len(allowed) == 1

    def test_a_console_echo_on_a_page_with_nothing_carded_is_still_hard(self):
        """The other control: no carded problem on the page, no excuse."""
        # Arrange
        problems = [
            "console.error: Failed to load resource: the server responded with a "
            "status of 404 (Not Found)",
        ]

        # Act
        hard, _allowed = classify_browser_problems(problems)

        # Assert
        assert len(hard) == 1

    def test_the_gallery_console_error_is_owned_explicitly(self):
        """It carries NO status code, so status matching cannot cover it. Naming it
        is the honest option; a generic rule would excuse unrelated console errors.
        """
        # Arrange
        problems = [
            "console.error: [Gallery] Could not open the demo figure: Error: Forbidden"
        ]

        # Act
        hard, allowed = classify_browser_problems(problems)

        # Assert
        assert hard == []
        assert allowed[0][1].startswith("hub-nginx-403s")

    def test_every_excused_problem_still_names_an_owner(self):
        """The allowlist must never contain an entry that excuses nothing."""
        for needle, card in KNOWN_BASE_BROWSER_PROBLEMS:
            assert needle, "an empty needle would excuse everything"
            assert card.startswith("hub-"), f"{needle!r} has no card"

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

    def test_the_capture_runs_the_production_derived_settings_module(self):
        """Not settings_dev: its static pipeline is not production's.

        Leader HOLD 2026-09-11: a DEBUG=0 capture under settings_dev still used
        plain StaticFilesStorage, WhiteNoise autorefresh and DevNoCache
        middleware, so the artifact could not evidence production static
        behaviour. Both the render step and the capture step must name the
        production-derived module.
        """
        for name in ("Migrate & start server", "Capture screenshots"):
            env = self._env_of(name)
            assert (
                env.get("SCITEX_HUB_DJANGO_SETTINGS_MODULE")
                == "config.settings.settings_screenshots"
            ), (
                f"{name} does not run config.settings.settings_screenshots "
                f"(env has {env.get('SCITEX_HUB_DJANGO_SETTINGS_MODULE')!r}). "
                "settings_dev renders with dev static/caching posture, so the "
                "artifact would not evidence production."
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


# ---------------------------------------------------------------------------
# The production-derived module must actually BE production-derived. These
# import it in a child interpreter (the same technique the scitex-umbrella
# guard uses) so a future edit cannot quietly revert it to dev posture and
# leave the workflow pointing at a module that no longer means what it says.
# ---------------------------------------------------------------------------


def _capture_settings_probe(code: str) -> subprocess.CompletedProcess:
    env = {**os.environ, **CHILD_ENV}
    # BOTH names, mirroring the workflow: plain Django reads
    # DJANGO_SETTINGS_MODULE, manage.py also honours the hub-prefixed alias.
    env["DJANGO_SETTINGS_MODULE"] = "config.settings.settings_screenshots"
    env["SCITEX_HUB_DJANGO_SETTINGS_MODULE"] = "config.settings.settings_screenshots"
    return subprocess.run(
        [sys.executable, "-c", code],
        cwd=str(REPO),
        env=env,
        capture_output=True,
        text=True,
    )


def test_the_capture_settings_resolve_to_the_production_static_pipeline():
    # Arrange / Act — import the real module under the CI env the job uses.
    result = _capture_settings_probe(
        "import django; django.setup()\n"
        "from django.conf import settings as s\n"
        "print('DEBUG', s.DEBUG)\n"
        "print('STORAGE', s.STORAGES['staticfiles']['BACKEND'])\n"
        "print('AUTOREFRESH', getattr(s, 'WHITENOISE_AUTOREFRESH', '<unset>'))\n"
        "print('DEV_MW', [m for m in s.MIDDLEWARE "
        "if 'DevNoCache' in m or 'BrowserReload' in m])\n"
    )
    # Assert
    assert result.returncode == 0, result.stderr
    out = result.stdout
    assert "DEBUG False" in out, out
    assert "STORAGE config.storage.HashedStaticFilesStorage" in out, out
    assert "AUTOREFRESH False" in out, out
    assert "DEV_MW []" in out, out


def test_the_hashed_backend_is_the_same_one_prod_and_staging_use():
    # Arrange — the identity that matters is that prod/staging opt in through
    # the same helper, so this is a claim about ONE pipeline, not two.
    # Act
    prod = (REPO / "config" / "settings" / "settings_prod.py").read_text(
        encoding="utf-8"
    )
    staging = (REPO / "config" / "settings" / "settings_staging.py").read_text(
        encoding="utf-8"
    )
    capture = (REPO / "config" / "settings" / "settings_screenshots.py").read_text(
        encoding="utf-8"
    )
    # Assert
    for name, text in (("prod", prod), ("staging", staging), ("capture", capture)):
        assert "hashed_storages(STORAGES)" in text, (
            f"{name} does not opt into the shared hashed static pipeline; the "
            "capture would then be evidencing a pipeline production does not run."
        )


class TestBrowserProblemsAreHardFailures:
    """The second half of the HOLD: report-only problems must fail the run."""

    def test_an_unowned_http_error_is_refused(self):
        # Arrange — a 4xx/5xx with no card behind it.
        problems = ["HTTP 500 http://127.0.0.1:8000/apps/writer/api/x/"]
        # Act / Assert
        with pytest.raises(AssertionError) as excinfo:
            assert_no_unowned_browser_problems(problems)
        assert "no card owns" in str(excinfo.value)

    def test_a_page_error_is_refused_even_if_a_url_is_allowlisted(self):
        # Arrange — uncaught exceptions are never excusable.
        problems = ["uncaught exception: TypeError: x is not a function"]
        # Act / Assert
        with pytest.raises(AssertionError):
            assert_no_unowned_browser_problems(problems)

    def test_the_known_cards_graph_500_is_excused_and_still_printed(self, capsys):
        # Arrange — the one measured base failure this capture must not own.
        problems = ["HTTP 500 http://127.0.0.1:8000/apps/cards/graph"]
        # Act
        assert_no_unowned_browser_problems(problems)
        # Assert — excused, and SAID SO on the run (a silent excusal is how an
        # allowlist rots).
        out = capsys.readouterr().out
        assert "excused" in out and "hub-cards-graph-500-store-unconfigured" in out

    def test_a_clean_page_reports_nothing(self):
        assert_no_unowned_browser_problems([])

    def test_every_excused_problem_names_an_owning_card(self):
        for needle, card in KNOWN_BASE_BROWSER_PROBLEMS:
            assert card and "-2026" in card, (
                f"allowlist entry {needle!r} does not name an owning card id; an "
                "exemption without an owner is how this guard gets disabled."
            )

    def test_browser_problem_log_still_records_http_errors(self):
        # Control: the classifier is fed by a log that must actually record
        # >=400 responses — otherwise every case above passes on an empty list
        # and the guard certifies nothing. Asserts BEHAVIOUR, not source text:
        # feed the log a synthetic response and read what it recorded.

        class _Resp:
            status = 500
            url = "http://127.0.0.1:8000/apps/x/api/y/"

        log = BrowserProblemLog()
        log._on_response(_Resp())

        # Assert
        recorded = log.drain()
        assert len(recorded) == 1, recorded
        assert recorded[0] == "HTTP 500 http://127.0.0.1:8000/apps/x/api/y/"

    def test_the_log_ignores_sub_400_responses(self):
        # The other half of the control: a 200 must NOT be recorded, or the
        # hard-failure test above would fail every clean page.
        class _Ok:
            status = 200
            url = "http://127.0.0.1:8000/apps/x/"

        log = BrowserProblemLog()
        log._on_response(_Ok())
        assert log.drain() == []
