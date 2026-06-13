"""URL configuration for scitex_live_paper_hub_app (path-B, user-published).

M4 ReReviewBadge end-to-end wiring uses the
:func:`scitex_agentic_journal.build_hub_resolver` adapter (journal PR
#34, ``_hub_app_publisher/``). The adapter is Protocol-shaped + has
zero live-paper imports: the wrapper passes in
``BundleContext / BundleSource / PaperState / RendererOptions``
factories and a ``load_paper`` callable; the adapter returns the
``(request, paper_id, **) -> BundleContext`` callable that
:func:`scitex_live_paper.mount` expects.

That keeps both sides decoupled per ADR-0002 SOC, and keeps THIS file
the only place the hub-specific URL shape leaks in (the
``hub_log_url_template`` argument tells the journal where the in-hub
submission-log endpoint lives — must match the agentic-journal hub
app's ``submission_log`` URL).

This file ships in the user-published ``scitex_live_paper_hub_app``
(NOT a hub built-in under ``apps/workspace/``) and gets stamped onto
the hub via ``scitex-hub app submit`` (publish-flow-step-5 — operator
action). See lead msg b3a51bec.
"""

from __future__ import annotations

from django.urls import include, path

from . import views


def _build_paper_urls():
    """Return the live-paper URL include with the hub_resolver wired in.

    Imports are deferred to call time so the package can be scaffold-
    validated on hosts that lack scitex-live-paper / scitex-agentic-
    journal (production hub deploys MUST have both — declared in this
    app's pyproject.toml).
    """
    from scitex_agentic_journal import build_hub_resolver
    from scitex_live_paper import (
        BundleContext,
        BundleSource,
        PaperState,
        RendererOptions,
        mount,
    )

    from .views import load_paper

    hub_resolver = build_hub_resolver(
        load_paper=load_paper,
        bundle_context_factory=BundleContext,
        bundle_source_factory=BundleSource,
        paper_state_factory=PaperState,
        renderer_options_factory=RendererOptions,
        # The hub mounts agentic-journal under /apps/agentic-journal/, so
        # the badge's log_url has to use that prefix (NOT the journal
        # default /aj/{paper_id}/log/ which is the standalone journal-
        # package URL shape).
        hub_log_url_template="/apps/agentic-journal/{paper_id}/log/",
    )
    return include(mount(resolver=hub_resolver))


app_name = "scitex_live_paper_hub_app"

urlpatterns = [
    path("", views.index_view, name="index"),
    # M4 path-B mount: /apps/live-paper/<paper_id>/
    path("<paper_id>/", _build_paper_urls()),
]
