"""URL config — forward to the upstream embedded app.

A future hub-side change (e.g. switching the mount path or wrapping
with hub auth middleware) lives here. Today the wrapper just
``include()``s the upstream patterns under the workspace's mount
point, preserving the upstream namespace so URL reverses stay
identical across deployments.
"""

from __future__ import annotations

from django.urls import include, path

urlpatterns = [
    path("", include("scitex_agentic_journal._django.urls")),
]
