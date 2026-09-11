#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""A production acceptance screenshot must PROVE it is a picture of production.

CARD: hub-screenshots-are-taken-with-debug-1-not-production-20260816.
LEADER RULING 2026-09-11: "Production acceptance screenshots must be captured
with DEBUG=0; DEBUG=1 screenshots may be supplemental but cannot satisfy
production verification."

THE DEFECT THIS EXISTS FOR. The capture job rendered every page with
``settings.DEBUG`` True, and the artifact was therefore a photograph of a
configuration that exists nowhere: Django's debug error pages instead of the
production 500/404 templates, static served through the finders instead of the
hashed production pipeline, and the dev-only footer bar
(``global_footer.html``, ``{% if DEBUG %}``) visible along the bottom edge of
the images that were about to go into a funding application.

WHY A MARKER-BASED CHECK AND NOT A FLAG ASSERTION. Asserting "the workflow
exports the production switch" is a statement about the workflow. The property
that matters is a statement about the RENDERED PAGE: did the thing a reviewer
is looking at come from a production configuration? So this module reads the
captured HTML for evidence that can only appear when DEBUG is True, and refuses
the capture when it finds any. That is the same shape as
``assert_pooled_visitor`` (session_role_check.py): the guard runs against the
artifact, in the consumer's context, not against a proxy for it.

THE TWO MARKERS, and why they are evidence rather than a whitelist:

1. The dev-only footer bar, keyed on ``footer-dev-tools`` and the six button
   ids. Its template block is ``{% if DEBUG %}``, so its presence is a direct
   statement that DEBUG was True for the request that produced this HTML. This
   is the symptom the operator actually saw in the delivered artifact.

2. The host Vite dev-server URL (``:5173/``). ``vite_script`` emits it under
   ``settings.DEBUG and not VITE_USE_BUILD``; nothing serves 5173 on a runner,
   so its presence means every platform entry failed to load. Measured
   2026-08-17 on run 32054829708: the whole frontend was detached from every
   screenshot this job had ever uploaded, and nothing errored.

The assertion is deliberately about ``DEBUG``'s OBSERVABLE CONSEQUENCES rather
than the flag's value: a capture can be taken with DEBUG=0 and still show a dev
marker if the page was cached, served by another process, or read from the
wrong file — and that capture is just as unfit to verify production.
"""

from __future__ import annotations

import re
from collections.abc import Sequence

__all__ = [
    "DEBUG_ONLY_MARKERS",
    "DEV_SERVER_ASSET_RE",
    "NotAProductionCaptureError",
    "assert_production_capture",
    "diagnose_capture_config",
    "find_debug_only_markers",
    "find_dev_server_asset_urls",
]

#: Substrings that exist in the rendered HTML ONLY under ``{% if DEBUG %}``
#: (templates/global_base_partials/global_footer.html:117). Ids rather than
#: human labels, because labels are translatable and ids are not: the capture
#: runs with a visitor session whose language may be JA.
DEBUG_ONLY_MARKERS = (
    "footer-dev-tools",
    "dev-tools-label",
    "page-refresh-btn",
    "clear-localstorage-btn",
    "init-visitor-pool-btn",
    "fill-visitor-slots-btn",
    "free-visitor-slots-btn",
    "cancel-all-jobs-btn",
)

#: The host Vite dev server, emitted only when DEBUG is on and VITE_USE_BUILD
#: is off. Port-anchored so a legitimate link containing "5173" elsewhere does
#: not fire.
DEV_SERVER_ASSET_RE = re.compile(r":5173/")

#: Where the captured page's configuration is written down, so a failure says
#: which page was unfit rather than just "a page".
WHAT_I_AM = "this page"


class NotAProductionCaptureError(AssertionError):
    """Raised when a captured page is not evidence of the production config."""


def find_debug_only_markers(rendered_html: str) -> list[str]:
    """Markers present in ``rendered_html`` that only a DEBUG page emits."""
    return [marker for marker in DEBUG_ONLY_MARKERS if marker in rendered_html]


def find_dev_server_asset_urls(rendered_html: str) -> list[str]:
    """The host Vite dev-server URLs in ``rendered_html``, in order."""
    return DEV_SERVER_ASSET_RE.findall(rendered_html)


def diagnose_capture_config(
    rendered_html: str,
    *,
    where: str = WHAT_I_AM,
) -> list[str]:
    """Every reason this page cannot verify production, as readable lines.

    Returns an empty list when the page is fit. Returning reasons rather than
    a bool keeps the failure message and the acceptance check reading the SAME
    evidence — the defect class this whole card is about.
    """
    problems: list[str] = []
    markers = find_debug_only_markers(rendered_html)
    if markers:
        problems.append(
            f"{where}: the dev-only footer bar is present ({', '.join(markers)}). "
            "That block is {% if DEBUG %} in "
            "templates/global_base_partials/global_footer.html, so this page "
            "was rendered with DEBUG=True and is not a picture of production."
        )
    dev_urls = find_dev_server_asset_urls(rendered_html)
    if dev_urls:
        problems.append(
            f"{where}: {len(dev_urls)} asset URL(s) point at the Vite DEV "
            "server (:5173/). Nothing serves that port in CI, so the frontend "
            "was detached from this page — a screenshot of it cannot show "
            "whether the product works."
        )
    return problems


def assert_production_capture(
    rendered_html: str,
    *,
    where: str = WHAT_I_AM,
    debug_declared: bool | None = None,
) -> None:
    """Refuse a capture that does not evidence a production configuration.

    :param rendered_html: the page's rendered HTML, as captured.
    :param where: the page label used in the failure message.
    :param debug_declared: the run's declared ``settings.DEBUG``, when the
        caller has it. ``True`` is refused on the DECLARATION alone — the
        point of the leader's ruling is that a DEBUG run may not satisfy
        production verification even if this particular page happens to look
        clean.

    Fail-loud by construction: no parameters, no configuration and no
    environment make this pass a DEBUG capture.
    """
    problems = diagnose_capture_config(rendered_html, where=where)
    if debug_declared:
        problems.insert(
            0,
            f"{where}: the capture declares DEBUG=True. Production acceptance "
            "screenshots must be taken with DEBUG=0 (leader ruling "
            "2026-09-11); a DEBUG capture may be supplemental, but it cannot "
            "satisfy production verification.",
        )
    if problems:
        raise NotAProductionCaptureError(
            "REFUSING this capture — it is not evidence of the production "
            "configuration, and a screenshot's whole value is fidelity:\n  "
            + "\n  ".join(problems)
            + "\nFix: run the acceptance capture with "
            "SCITEX_HUB_DJANGO_DEBUG=0 (settings_dev.py:64 reads that name; a "
            "bare `DEBUG` env var is read only by settings_prod/staging and is "
            "INERT under settings_dev) and keep SCITEX_HUB_VITE_USE_BUILD=1 so "
            "the built manifest is used."
        )


def assert_capture_sequence(
    pages: Sequence[tuple[str, str]],
    *,
    debug_declared: bool | None = None,
) -> None:
    """Refuse the whole run if ANY captured page fails the check.

    Separate from :func:`assert_production_capture` so a caller can report
    every unfit page at once instead of failing on the first — a run that
    uploads eleven good images and one DEBUG image is still an unfit artifact.
    """
    problems: list[str] = []
    for where, rendered_html in pages:
        try:
            assert_production_capture(
                rendered_html, where=where, debug_declared=debug_declared
            )
        except NotAProductionCaptureError as exc:
            problems.append(str(exc))
    if problems:
        raise NotAProductionCaptureError("\n".join(problems))
