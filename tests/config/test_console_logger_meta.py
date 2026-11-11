"""Only a DEBUG host advertises the optional console upload endpoint."""
from pathlib import Path

import pytest
from django.http import HttpResponse
from django.template import Context, Engine
from django.test import RequestFactory, override_settings
from django.urls import include, path

from config.context_processors import debug_mode


urlpatterns = [path("owned/dev/", include(([
    path("api/console/", HttpResponse, name="console_log"),
], "dev_app")))]


@pytest.mark.parametrize("enabled,expected", [
    (False, ""),
    (True, '<meta name="scitex-console-log-endpoint" content="/owned/dev/api/console/" />'),
])
def test_console_upload_metadata_follows_the_host_debug_setting(enabled, expected):
    # Arrange
    templates = Path(__file__).resolve().parents[2] / "templates"
    template = Engine(dirs=[str(templates)]).get_template(
        "global_base_partials/console_logger_meta.html")
    request = RequestFactory().get("/")
    # Act
    with override_settings(DEBUG=enabled, ROOT_URLCONF=__name__):
        rendered = template.render(Context(debug_mode(request))).strip()
    # Assert
    assert rendered == expected
