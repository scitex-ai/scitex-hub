"""The host supplies registry ownership; SDK owns the actual header action."""

from types import SimpleNamespace

import pytest
from django.http import HttpResponse
from django.test import RequestFactory

from apps.infra.workspace_app._api_docs_metadata import inject_api_docs_metadata

HTML = "<html><head></head><body><div data-stx-app-header></div></body></html>"


def owner(package="Demo_Leaf", url="/apps/demo/"):
    return SimpleNamespace(pip_package=package, get_url=lambda: url)


def test_registered_owner_stamps_normalized_sdk_input_without_changing_controls():
    # Arrange
    request = RequestFactory().get("/apps/demo/?project=private-selection")
    response = HttpResponse(HTML)
    response["Content-Length"] = str(len(response.content))
    response["ETag"] = "old"
    # Act
    inject_api_docs_metadata(request, response, modules=[owner()])
    # Assert
    assert (
        b'data-stx-api-docs-url="/docs/web-api/?package=demo-leaf"' in response.content,
        b"private-selection" in response.content,
        b"data-stx-app-header" in response.content,
        int(response["Content-Length"]) == len(response.content),
        response.get("ETag"),
    ) == (True, False, True, True, None)


@pytest.mark.parametrize(
    "path", ["/apps/demo-neighbor/", "/accounts/", "/docs/web-api/"]
)
def test_other_paths_do_not_acquire_another_apps_identity(path):
    # Arrange
    request = RequestFactory().get(path)
    response = HttpResponse(HTML)
    # Act
    inject_api_docs_metadata(request, response, modules=[owner()])
    # Assert
    assert response.content == HTML.encode()


def test_embedded_document_gets_metadata_without_host_header_or_business_calls():
    # Arrange
    request = RequestFactory().get("/apps/demo/?embed=1", HTTP_SEC_FETCH_DEST="iframe")
    response = HttpResponse(HTML)
    # Act
    inject_api_docs_metadata(request, response, modules=[owner()])
    # Assert
    assert (
        b"data-stx-api-docs-url" in response.content,
        b"mobile-hamburger-btn" in response.content,
    ) == (True, False)


@pytest.mark.parametrize("package", ["", "../private", "/outside"])
def test_missing_or_invalid_owner_is_not_guessed_from_app_label(package):
    # Arrange
    response = HttpResponse(HTML)
    request = RequestFactory().get("/apps/demo/")
    # Act
    inject_api_docs_metadata(request, response, modules=[owner(package)])
    # Assert
    assert response.content == HTML.encode()


def test_fragment_and_non_html_are_not_rewritten():
    # Arrange
    request = RequestFactory().get("/apps/demo/")
    fragment = HttpResponse("<section>fragment</section>")
    data = HttpResponse('{"ok":true}', content_type="application/json")
    # Act
    inject_api_docs_metadata(request, fragment, modules=[owner()])
    inject_api_docs_metadata(request, data, modules=[owner()])
    # Assert
    assert (fragment.content, data.content) == (
        b"<section>fragment</section>",
        b'{"ok":true}',
    )
