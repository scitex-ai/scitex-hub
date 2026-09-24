"""The Hub's /apps/stats/ mount never answers without a signed-in user.

scitex-stats' own Django views carry no login gate, so the Hub adapter is
the only thing standing between an anonymous visitor and test execution,
project file reads, and artifact writes (the sec-working-dir-passthrough-
family pattern: writer SITE 3, storage SITE 4). These tests pin the gate on
every delegated view, and pin that the mount resolves to the gated wrapper
— not the raw upstream URLconf.
"""

from __future__ import annotations

import pytest
from django.contrib.auth.models import AnonymousUser
from django.test import RequestFactory

from apps.workspace.stats_app import views

_ANONYMOUS_PATHS = (
    ("/apps/stats/", "index", {}),
    ("/apps/stats/api/health", "health", {}),
    ("/apps/stats/api/project-scope", "project_scope", {}),
    ("/apps/stats/api/project-files", "project_files", {}),
    ("/apps/stats/api/project-import", "project_import", {}),
    ("/apps/stats/api/project-save", "project_save", {}),
    ("/apps/stats/api/tests", "tests", {}),
    ("/apps/stats/api/recommend", "recommend", {}),
    ("/apps/stats/api/recommend-test", "recommend_test", {}),
    ("/apps/stats/api/run-all", "run_all", {}),
    ("/apps/stats/api/run", "run", {}),
    ("/apps/stats/api/describe", "describe", {}),
    ("/apps/stats/api/effect-size", "effect_size", {}),
    ("/apps/stats/api/power", "power", {}),
    ("/apps/stats/api/posthoc", "posthoc", {}),
    ("/apps/stats/api/correct", "correct", {}),
    ("/apps/stats/api/plot", "plot", {}),
    ("/apps/stats/api/integrations", "integrations", {}),
    ("/apps/stats/api/report/capabilities", "report_capabilities", {}),
    ("/apps/stats/api/report/pdf", "report_pdf", {}),
    ("/apps/stats/api/report/save", "report_save", {}),
)


@pytest.mark.parametrize(("url", "view_name", "kwargs"), _ANONYMOUS_PATHS)
def test_anonymous_visitor_is_redirected_to_login(url, view_name, kwargs):
    # Arrange: the real view, so a missing gate would fall through to stats
    request = RequestFactory().get(url)
    request.user = AnonymousUser()
    view = getattr(views, view_name)

    # Act
    response = view(request, **kwargs)

    # Assert: login_required short-circuits before any upstream delegate runs
    assert response.status_code == 302
    assert "/auth/login/" in response["Location"]


def test_root_urlconf_resolves_stats_to_the_gated_index_when_installed():
    # Arrange
    pytest.importorskip("scitex_stats._django.urls")
    from django.urls import resolve

    # Act
    match = resolve("/apps/stats/")

    # Assert
    assert match.view_name == "stats:index"
    assert match.func.__module__ == "apps.workspace.stats_app.views"
