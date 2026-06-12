"""URL config — forward to the upstream embedded app.

The hub wrapper currently uses the **single-tenant env-pinned** path:
the upstream ``_django/urls.py`` reads ``SCITEX_LIVE_PAPER_BUNDLE``
to find the bundle for the live-paper viewer. Multi-tenant routing
via ``scitex_live_paper.mount(resolver=...)`` is a follow-up once
the upstream's ``BundleContext`` dataclass is publicly importable.

A future hub-side change (e.g. switching to ``mount(resolver=...)``
or adding hub-auth middleware) lives here. Today the wrapper just
``include()``s the upstream patterns under the workspace's mount
point. The upstream URL conf declares ``app_name = "live_paper"`` so
reverses (``reverse("live_paper:viewer_page")``) stay stable across
deployments without an explicit ``namespace=`` argument.
"""

from __future__ import annotations

from django.urls import include, path

urlpatterns = [
    path("", include("scitex_live_paper._django.urls")),
]
