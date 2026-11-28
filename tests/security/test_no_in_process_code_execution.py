"""Regression: the web server never runs user code in its own process.

The console's early execute / analysis / notebook / environment-setup /
workflow endpoints ran user-supplied Python, pip installs and notebook
kernels inside the web application process. They are retired (410).

Real URLconf through the Django test client, a signed-in non-staff user,
a temporary MEDIA_ROOT (where environments used to be created). No mocks.
"""

from __future__ import annotations

import json
from uuid import uuid4

import pytest
from django.contrib.auth.models import User

pytestmark = [pytest.mark.security, pytest.mark.django_db]

NB = "00000000-0000-0000-0000-000000000001"

ROUTES = [
    "/apps/console/execute/",
    "/apps/console/analysis/run/",
    f"/apps/console/notebooks/{NB}/execute/",
    "/apps/console/environments/env1/setup/",
    "/apps/console/environments/env1/execute/",
    "/apps/console/workflows/wf1/execute/",
]

PAYLOAD = json.dumps(
    {"code": "open('PWNED','w').write('x')", "requirements": ["./evil"]}
)


@pytest.fixture
def signed_in(client, settings, tmp_path):
    settings.MEDIA_ROOT = str(tmp_path / "media")
    user = User.objects.create_user(username=f"u-{uuid4().hex[:10]}")
    client.force_login(user)
    return client


@pytest.mark.parametrize("url", ROUTES)
def test_execution_route_is_gone(signed_in, url):
    # Arrange
    body = PAYLOAD
    # Act
    response = signed_in.post(url, body, content_type="application/json")
    # Assert
    assert response.status_code == 410


@pytest.mark.parametrize("url", ROUTES)
def test_execution_route_creates_nothing_on_disk(signed_in, settings, url, tmp_path):
    # Arrange
    body = PAYLOAD
    # Act
    signed_in.post(url, body, content_type="application/json")
    # Assert
    assert not (tmp_path / "media").exists()
