"""Files app HTTP API: uploads land where asked; one user never reaches another."""

import json

from django.contrib.auth.models import AnonymousUser, User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import RequestFactory, override_settings

from apps.workspace.files_app import views
from apps.workspace.files_app.services import workspace_fs as fs


def _as(user, request):
    request.user = user
    return request


def test_upload_lands_in_the_chosen_folder(tmp_path):
    # Arrange
    alice = User(username="alice")
    rf = RequestFactory()
    with override_settings(BASE_DIR=tmp_path):
        (fs.user_root(alice) / "Downloads" / "figures").mkdir()
        request = _as(
            alice,
            rf.post(
                "/apps/files/api/upload/",
                {
                    "path": "Downloads/figures",
                    "files": [
                        SimpleUploadedFile("a.csv", b"x,y"),
                        SimpleUploadedFile("b.csv", b"1,2"),
                    ],
                },
            ),
        )
        # Act
        views.api_upload(request)
    # Assert
    folder = tmp_path / "data/users/alice/Downloads/figures"
    assert sorted(p.name for p in folder.iterdir()) == ["a.csv", "b.csv"]


def test_upload_outside_the_root_is_refused(tmp_path):
    # Arrange
    alice = User(username="alice")
    request = _as(
        alice,
        RequestFactory().post(
            "/apps/files/api/upload/",
            {"path": "../bob", "files": [SimpleUploadedFile("x.txt", b"x")]},
        ),
    )
    # Act
    with override_settings(BASE_DIR=tmp_path):
        response = views.api_upload(request)
    # Assert
    assert response.status_code == 400


def test_another_user_cannot_list_a_workspace(tmp_path):
    # Arrange
    bob = User(username="bob")
    request = _as(bob, RequestFactory().get("/apps/files/api/list/", {"path": "../alice"}))
    # Act
    with override_settings(BASE_DIR=tmp_path):
        fs.user_root(User(username="alice"))
        response = views.api_list(request)
    # Assert
    assert response.status_code == 400


def test_another_user_cannot_download_a_file(tmp_path):
    # Arrange
    bob = User(username="bob")
    request = _as(
        bob,
        RequestFactory().get(
            "/apps/files/download/", {"path": "../alice/Downloads/secret.txt"}
        ),
    )
    with override_settings(BASE_DIR=tmp_path):
        alice_root = fs.user_root(User(username="alice"))
        (alice_root / "Downloads" / "secret.txt").write_text("alice only")
        # Act
        response = views.download(request)
    # Assert
    assert response.status_code == 400


def test_same_relative_path_only_ever_reads_your_own_root(tmp_path):
    # Arrange
    bob = User(username="bob")
    request = _as(
        bob, RequestFactory().get("/apps/files/download/", {"path": "Downloads/secret.txt"})
    )
    with override_settings(BASE_DIR=tmp_path):
        alice_root = fs.user_root(User(username="alice"))
        (alice_root / "Downloads" / "secret.txt").write_text("alice only")
        # Act
        response = views.download(request)
    # Assert
    assert response.status_code == 404


def test_listing_names_only_your_own_entries(tmp_path):
    # Arrange
    alice = User(username="alice")
    request = _as(alice, RequestFactory().get("/apps/files/api/list/", {"path": ""}))
    # Act
    with override_settings(BASE_DIR=tmp_path):
        response = views.api_list(request)
    # Assert
    assert [e["name"] for e in json.loads(response.content)["entries"]] == [
        "Downloads",
        "Recordings",
    ]


def test_anonymous_visitor_is_sent_to_login(tmp_path):
    # Arrange
    request = _as(AnonymousUser(), RequestFactory().get("/apps/files/api/list/"))
    # Act
    with override_settings(BASE_DIR=tmp_path):
        response = views.api_list(request)
    # Assert
    assert response.status_code == 302
