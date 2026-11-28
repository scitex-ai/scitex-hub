"""Regression: files under MEDIA_ROOT are served only to readers allowed to see them.

``/media/`` used to be served straight from disk, and MEDIA_ROOT holds
private user data at predictable paths (``notebooks/<user id>/``,
``users/<user id>/workspace``, uploaded BibTeX, compiled manuscripts ...).
Media now goes through ``apps.infra.platform_app.views.media.serve_media``,
which applies ``media_access`` and answers 404 to anyone else.

Real files under a temporary MEDIA_ROOT, real users and rows in the test
database, the real URLconf through the Django test client. No mocks.
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from django.contrib.auth.models import User

pytestmark = [pytest.mark.security, pytest.mark.django_db]


@pytest.fixture
def media_root(settings, tmp_path):
    root = tmp_path / "media"
    root.mkdir()
    settings.MEDIA_ROOT = str(root)
    return root


@pytest.fixture
def alice():
    return User.objects.create_user(username=f"alice-{uuid4().hex[:10]}")


@pytest.fixture
def bob():
    return User.objects.create_user(username=f"bob-{uuid4().hex[:10]}")


@pytest.fixture
def alice_notebook(media_root, alice):
    path = media_root / "notebooks" / str(alice.pk) / "analysis.ipynb"
    path.parent.mkdir(parents=True)
    path.write_text('{"cells": []}')
    return f"/media/notebooks/{alice.pk}/analysis.ipynb"


@pytest.fixture
def public_avatar(media_root):
    path = media_root / "avatars" / "face.png"
    path.parent.mkdir(parents=True)
    path.write_bytes(b"\x89PNG\r\n\x1a\n")
    return "/media/avatars/face.png"


@pytest.fixture
def alice_bibtex(media_root, alice):
    from apps.workspace.scholar_app.models import BibTeXEnrichmentJob

    name = "bibtex_uploads/2026/11/28/refs.bib"
    path = media_root / name
    path.parent.mkdir(parents=True)
    path.write_text("@article{a, title={x}}")
    BibTeXEnrichmentJob.objects.create(user=alice, input_file=name)
    return f"/media/{name}"


@pytest.fixture
def unlisted_file(media_root):
    path = media_root / "cgroups" / "state.json"
    path.parent.mkdir(parents=True)
    path.write_text("{}")
    return "/media/cgroups/state.json"


def _get(client, url, user=None, **extra):
    if user is not None:
        client.force_login(user)
    return client.get(url, **extra)


# --------------------------------------------------------------------------- #
# Per-user paths                                                               #
# --------------------------------------------------------------------------- #
def test_anonymous_cannot_read_private_notebook(client, alice_notebook):
    # Arrange
    url = alice_notebook
    # Act
    response = _get(client, url)
    # Assert
    assert response.status_code == 404


def test_other_user_cannot_read_private_notebook(client, alice_notebook, bob):
    # Arrange
    url = alice_notebook
    # Act
    response = _get(client, url, bob)
    # Assert
    assert response.status_code == 404


def test_owner_reads_own_notebook(client, alice_notebook, alice):
    # Arrange
    url = alice_notebook
    # Act
    response = _get(client, url, alice)
    # Assert
    assert response.status_code == 200


def test_private_media_is_not_cacheable(client, alice_notebook, alice):
    # Arrange
    url = alice_notebook
    # Act
    response = _get(client, url, alice)
    # Assert
    assert response["Cache-Control"] == "private, no-store"


# --------------------------------------------------------------------------- #
# Field-backed uploads                                                         #
# --------------------------------------------------------------------------- #
def test_other_user_cannot_read_uploaded_bibtex(client, alice_bibtex, bob):
    # Arrange
    url = alice_bibtex
    # Act
    response = _get(client, url, bob)
    # Assert
    assert response.status_code == 404


def test_uploader_reads_own_bibtex(client, alice_bibtex, alice):
    # Arrange
    url = alice_bibtex
    # Act
    response = _get(client, url, alice)
    # Assert
    assert response.status_code == 200


# --------------------------------------------------------------------------- #
# Public assets, unlisted prefixes, path tricks                                #
# --------------------------------------------------------------------------- #
def test_anonymous_reads_public_avatar(client, public_avatar):
    # Arrange
    url = public_avatar
    # Act
    response = _get(client, url)
    # Assert
    assert response.status_code == 200


def test_unlisted_prefix_is_refused_even_when_signed_in(client, unlisted_file, alice):
    # Arrange
    url = unlisted_file
    # Act
    response = _get(client, url, alice)
    # Assert
    assert response.status_code == 404


@pytest.mark.parametrize(
    "suffix",
    [
        "avatars/../notebooks/{uid}/analysis.ipynb",
        "avatars/%2e%2e/notebooks/{uid}/analysis.ipynb",
        "avatars/%252e%252e/notebooks/{uid}/analysis.ipynb",
    ],
)
def test_public_prefix_cannot_be_used_to_reach_private_files(
    client, alice_notebook, alice, suffix
):
    # Arrange
    url = "/media/" + suffix.format(uid=alice.pk)
    # Act
    response = _get(client, url)
    # Assert
    assert response.status_code == 404


# --------------------------------------------------------------------------- #
# nginx hand-off                                                               #
# --------------------------------------------------------------------------- #
def test_behind_nginx_the_file_is_handed_off_internally(client, alice_notebook, alice):
    # Arrange
    headers = {"HTTP_X_MEDIA_ACCEL_PREFIX": "/_protected_media/"}
    # Act
    response = _get(client, alice_notebook, alice, **headers)
    # Assert
    assert response["X-Accel-Redirect"] == (
        f"/_protected_media/notebooks/{alice.pk}/analysis.ipynb"
    )


def test_hand_off_is_not_used_for_a_refused_request(client, alice_notebook, bob):
    # Arrange
    headers = {"HTTP_X_MEDIA_ACCEL_PREFIX": "/_protected_media/"}
    # Act
    response = _get(client, alice_notebook, bob, **headers)
    # Assert
    assert "X-Accel-Redirect" not in response
