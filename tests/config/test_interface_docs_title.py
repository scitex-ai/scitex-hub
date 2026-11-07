"""Interface documentation names its own browser tab, without project leakage."""

from types import SimpleNamespace

import pytest
from django.test import override_settings

from apps.infra.project_app.templatetags.branding_tags import page_title


@pytest.mark.parametrize(
    "environment,expected",
    [("production", "Web API"), ("development", "Web API (dev)")],
)
def test_provider_documentation_title_uses_the_canonical_section(environment, expected):
    # Arrange
    context = {
        "request": SimpleNamespace(path="/docs/web-api/"),
        "current_project": SimpleNamespace(
            name="private-project", slug="private-project"
        ),
    }
    # Act
    with override_settings(SCITEX_ENV=environment, SCITEX_APP_MODE="hub"):
        title = page_title(context)
    # Assert
    assert title == expected
