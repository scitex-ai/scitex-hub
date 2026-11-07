"""The mounted leaf reads and writes Hub's persistent per-user library."""

import json
import os
import uuid

import pytest
from django.contrib.auth.models import AnonymousUser, User
from django.core.exceptions import PermissionDenied
from django.test import RequestFactory, override_settings
from django.urls import resolve


@pytest.fixture
def library_users(tmp_path):
    users_root = tmp_path / "users"
    users = [User(username=f"leaf-library-{uuid.uuid4().hex}") for _ in range(2)]
    setting = "SCITEX_SCHOLAR_MOUNTED_LIBRARY_BASE"
    previous = os.environ.get(setting)
    os.environ[setting] = str(tmp_path / "unbound-service-library")
    try:
        with override_settings(USER_DATA_ROOT=users_root):
            yield users_root, users
    finally:
        if previous is None:
            os.environ.pop(setting, None)
        else:
            os.environ[setting] = previous


def _library(users_root, user):
    return users_root / user.username / ".scitex" / "scholar" / "library"


def _request(user, data=None):
    factory = RequestFactory()
    request = (
        factory.get("/apps/scholar/api/library")
        if data is None
        else factory.post("/apps/scholar/api/library/import", data)
    )
    request.user = user
    return request


@pytest.mark.parametrize("selected", [0, 1])
def test_leaf_reads_only_the_authenticated_users_persistent_library(
    library_users, selected
):
    # Arrange
    users_root, users = library_users
    for index, user in enumerate(users):
        primary = _library(users_root, user) / "MASTER" / f"PAPER{index}"
        primary.mkdir(parents=True)
        (primary / "metadata.json").write_text(
            json.dumps({"metadata": {"basic": {"title": f"Owner {index} paper"}}})
        )
    # Act
    response = resolve("/apps/scholar/api/library").func(_request(users[selected]))
    payload = json.loads(response.content)
    # Assert
    assert (response.status_code, [p["paper_id"] for p in payload["papers"]]) == (
        200,
        [f"PAPER{selected}"],
    )


def test_listing_an_empty_library_does_not_initialize_it(library_users):
    # Arrange
    users_root, users = library_users
    # Act
    response = resolve("/apps/scholar/api/library").func(_request(users[0]))
    # Assert
    assert (response.status_code, _library(users_root, users[0]).exists()) == (
        200,
        False,
    )


def test_anonymous_library_request_is_gated_before_path_resolution(library_users):
    # Arrange
    users_root, _ = library_users
    # Act
    response = resolve("/apps/scholar/api/library").func(_request(AnonymousUser()))
    # Assert
    assert (response.status_code, users_root.exists()) == (302, False)


def test_leaf_import_writes_only_to_the_authenticated_users_library(library_users):
    # Arrange
    users_root, users = library_users
    bibliography = """@article{scope_control,
        title={Library scope control}, author={Reader, Alice}, year={2026}
    }"""
    # Act
    response = resolve("/apps/scholar/api/library/import").func(
        _request(users[0], {"bibtex": bibliography})
    )
    owned = list((_library(users_root, users[0]) / "MASTER").glob("*/metadata.json"))
    # Assert
    assert (
        response.status_code,
        len(owned),
        _library(users_root, users[1]).exists(),
    ) == (
        200,
        1,
        False,
    )


@pytest.mark.parametrize("username", ["..", ".", "../outside", "/outside", "a\\b"])
def test_library_binding_refuses_unsafe_owner_components(library_users, username):
    # Arrange
    user = User(username=username)
    # Act / Assert
    with pytest.raises(PermissionDenied):
        resolve("/apps/scholar/api/library").func(_request(user))
