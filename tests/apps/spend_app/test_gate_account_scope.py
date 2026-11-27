"""Spend controls apply to stored, signed-in accounts only.

Anyone else (an anonymous visitor, a request no auth middleware populated, an
unsaved user object) passes the gate untouched, so the wrapped view's own
access check answers them instead of the gate crashing or refusing.
"""

from django.contrib.auth.models import AnonymousUser, User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.http import HttpResponse
from django.test import RequestFactory

from apps.infra.spend_app.decorators import storage_write
from apps.infra.spend_app.services import gate


def _view(request):
    return HttpResponse("view ran", status=200)


def _upload_request():
    return RequestFactory().post(
        "/upload/", {"files": [SimpleUploadedFile("a.txt", b"x")]}
    )


def test_an_anonymous_user_has_no_account() -> None:
    # Arrange
    user = AnonymousUser()
    # Act
    result = gate.has_account(user)
    # Assert
    assert result is False


def test_an_unsaved_user_has_no_account() -> None:
    # Arrange
    user = User(username="unsaved")
    # Act
    result = gate.has_account(user)
    # Assert
    assert result is False


def test_a_request_without_a_user_reaches_the_view() -> None:
    # Arrange
    request = _upload_request()
    # Act
    response = storage_write(_view)(request)
    # Assert
    assert response.content == b"view ran"


def test_an_unsaved_user_upload_reaches_the_view() -> None:
    # Arrange
    request = _upload_request()
    request.user = User(username="unsaved")
    # Act
    response = storage_write(_view)(request)
    # Assert
    assert response.content == b"view ran"
