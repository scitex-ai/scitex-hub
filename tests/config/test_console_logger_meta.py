"""The console upload endpoint is advertised only to staff, and only when dev tools are on."""

from pathlib import Path

import pytest
from django.contrib.auth.models import AnonymousUser
from django.http import HttpResponse
from django.template import Context, Engine
from django.test import RequestFactory, override_settings
from django.urls import include, path

from config.context_processors import debug_mode

urlpatterns = [
    path(
        "owned/dev/",
        include(
            (
                [
                    path("api/console/", HttpResponse, name="console_log"),
                ],
                "dev_app",
            )
        ),
    )
]

META = '<meta name="scitex-console-log-endpoint" content="/owned/dev/api/console/" />'


class _Staff:
    is_staff = True
    is_superuser = False


class _Regular:
    is_staff = False
    is_superuser = False


@pytest.mark.parametrize(
    "enabled,debug,user,expected",
    [
        (False, False, _Staff(), ""),
        (False, True, _Staff(), ""),
        (True, False, AnonymousUser(), ""),
        (True, True, _Regular(), ""),
        (True, False, _Staff(), META),
    ],
)
def test_console_upload_metadata_needs_dev_tools_and_staff(
    enabled, debug, user, expected
):
    # Arrange
    templates = Path(__file__).resolve().parents[2] / "templates"
    template = Engine(dirs=[str(templates)]).get_template(
        "global_base_partials/console_logger_meta.html"
    )
    request = RequestFactory().get("/")
    # Act
    with override_settings(
        DEV_TOOLS_ENABLED=enabled, DEBUG=debug, ROOT_URLCONF=__name__
    ):
        context = {**debug_mode(request), "user": user}
        rendered = template.render(Context(context)).strip()
    # Assert
    assert rendered == expected
