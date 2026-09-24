"""Login-gated delegates to the optional scitex-stats Django app.

The upstream package owns the statistics UI and its project-scoped file
contract (``scitex_stats._django._projects``: request-aware provider, Hub
owns authorization via ``SCITEX_PROJECT_PROVIDER``). The Hub owns the public
route and its login boundary, so every upstream view is delegated through
this module instead of mounting the package URLconf raw — the raw mount
answered 200 with no user at all (the sec-working-dir-passthrough-family
pattern: writer SITE 3, storage SITE 4).

Imports stay inside each call because scitex-stats is an optional sibling.
A Hub installation without it must still import settings, collect tests,
and serve every unrelated app; config/urls.py omits this mount in that
case.
"""

from __future__ import annotations

from django.contrib.auth.decorators import login_required


def _delegate(view_name, request, *args, **kwargs):
    from scitex_stats._django import views as upstream

    return getattr(upstream, view_name)(request, *args, **kwargs)


def _delegate_plot(view_name, request, *args, **kwargs):
    from scitex_stats._django import _plot_views as upstream

    return getattr(upstream, view_name)(request, *args, **kwargs)


def _delegate_report(view_name, request, *args, **kwargs):
    from scitex_stats._django import _report_views as upstream

    return getattr(upstream, view_name)(request, *args, **kwargs)


_project_scope_view = None


@login_required
def index(request):
    return _delegate("index", request)


@login_required
def health(request):
    return _delegate("health", request)


@login_required
def project_scope(request):
    """The picker's HTTP contract, served with the host's provider.

    The view is constructed the same way as in the upstream URLconf
    (``project_listing_view(_projects.provider)``); ``_projects.provider``
    resolves the Hub's ``SCITEX_PROJECT_PROVIDER`` per request, so the
    authorization owner does not change — only the login boundary is added.
    """
    global _project_scope_view
    if _project_scope_view is None:
        from scitex_ui.project_scope import project_listing_view

        from scitex_stats._django import _projects

        _project_scope_view = project_listing_view(_projects.provider)
    return _project_scope_view(request)


@login_required
def project_files(request):
    return _delegate("project_files", request)


@login_required
def project_import(request):
    return _delegate("project_import", request)


@login_required
def project_save(request):
    return _delegate("project_save", request)


@login_required
def tests(request):
    return _delegate("tests", request)


@login_required
def recommend(request):
    return _delegate("recommend", request)


@login_required
def recommend_test(request):
    return _delegate("recommend_test", request)


@login_required
def run_all(request):
    return _delegate("run_all", request)


@login_required
def run(request):
    return _delegate("run", request)


@login_required
def describe(request):
    return _delegate("describe", request)


@login_required
def effect_size(request):
    return _delegate("effect_size", request)


@login_required
def power(request):
    return _delegate("power", request)


@login_required
def posthoc(request):
    return _delegate("posthoc", request)


@login_required
def correct(request):
    return _delegate("correct", request)


@login_required
def plot(request):
    return _delegate_plot("plot", request)


@login_required
def integrations(request):
    return _delegate_plot("integrations", request)


@login_required
def report_capabilities(request):
    return _delegate_report("report_capabilities", request)


@login_required
def report_pdf(request):
    return _delegate_report("report_pdf", request)


@login_required
def report_save(request):
    return _delegate_report("report_save", request)


__all__ = [
    "correct",
    "describe",
    "effect_size",
    "health",
    "index",
    "integrations",
    "plot",
    "posthoc",
    "power",
    "project_files",
    "project_import",
    "project_save",
    "project_scope",
    "recommend",
    "recommend_test",
    "report_capabilities",
    "report_pdf",
    "report_save",
    "run",
    "run_all",
    "tests",
]
