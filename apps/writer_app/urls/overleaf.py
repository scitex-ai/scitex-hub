"""Writer App Overleaf URLs - Import/export endpoints."""

from django.urls import path

from ..views.overleaf.api import api_export_overleaf, api_import_overleaf

urlpatterns = [
    path("import/", api_import_overleaf, name="api_overleaf_import"),
    path("export/", api_export_overleaf, name="api_overleaf_export"),
]
