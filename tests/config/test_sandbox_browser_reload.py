"""The actual reload middleware respects artifact mode and sandbox CSP."""

from asgiref.sync import async_to_sync
from django.http import HttpResponse
from django.test import RequestFactory, override_settings
from django.urls import include, path

from config.dev_browser_reload import SandboxAwareBrowserReloadMiddleware

urlpatterns = [path("__reload__/", include("django_browser_reload.urls"))]


def response(policy=""):
    result = HttpResponse("<html><body>Chart</body></html>")
    if policy:
        result["Content-Security-Policy"] = policy
    return result


@override_settings(DEBUG=True, ROOT_URLCONF=__name__, SCITEX_HUB_FRONTEND_MODE="build")
def test_opaque_sandbox_does_not_receive_worker():
    for policy in ("sandbox allow-scripts", "default-src 'self'; sandbox"):
        middleware = SandboxAwareBrowserReloadMiddleware(
            lambda request, policy=policy: response(policy)
        )
        result = middleware(RequestFactory().get("/chart/"))
        assert b"reload-listener" not in result.content
        assert result["Content-Security-Policy"] == policy


@override_settings(DEBUG=True, ROOT_URLCONF=__name__, SCITEX_HUB_FRONTEND_MODE="build")
def test_regular_and_same_origin_pages_keep_reload():
    for policy in ("", "sandbox allow-scripts allow-same-origin"):
        middleware = SandboxAwareBrowserReloadMiddleware(
            lambda request, policy=policy: response(policy)
        )
        result = middleware(RequestFactory().get("/"))
        assert b"reload-listener" in result.content


@override_settings(DEBUG=True, ROOT_URLCONF=__name__, SCITEX_HUB_FRONTEND_MODE="build")
def test_async_sandbox_response_keeps_same_protection():
    async def view(request):
        return response("sandbox allow-scripts")

    middleware = SandboxAwareBrowserReloadMiddleware(view)
    result = async_to_sync(middleware)(RequestFactory().get("/chart/"))
    assert b"reload-listener" not in result.content


@override_settings(DEBUG=True, ROOT_URLCONF=__name__, SCITEX_HUB_FRONTEND_MODE="baked")
def test_baked_frontend_keeps_page_content_without_reload_worker():
    # Arrange
    middleware = SandboxAwareBrowserReloadMiddleware(lambda request: response())
    # Act
    result = middleware(RequestFactory().get("/"))
    # Assert
    assert result.content == b"<html><body>Chart</body></html>"


@override_settings(DEBUG=True, ROOT_URLCONF=__name__, SCITEX_HUB_FRONTEND_MODE="baked")
def test_baked_frontend_preserves_same_origin_sandbox_and_content():
    # Arrange
    policy = "sandbox allow-scripts allow-same-origin"
    middleware = SandboxAwareBrowserReloadMiddleware(lambda request: response(policy))
    # Act
    result = middleware(RequestFactory().get("/chart/"))
    # Assert
    assert (result["Content-Security-Policy"], result.content) == (
        policy,
        b"<html><body>Chart</body></html>",
    )


@override_settings(DEBUG=True, ROOT_URLCONF=__name__, SCITEX_HUB_FRONTEND_MODE="baked")
def test_async_baked_frontend_keeps_page_without_reload_worker():
    # Arrange
    async def view(request):
        return response()

    middleware = SandboxAwareBrowserReloadMiddleware(view)
    # Act
    result = async_to_sync(middleware)(RequestFactory().get("/"))
    # Assert
    assert result.content == b"<html><body>Chart</body></html>"


@override_settings(
    DEBUG=True,
    ROOT_URLCONF=__name__,
    SCITEX_HUB_FRONTEND_MODE="build",
    VITE_USE_BUILD=True,
)
def test_build_mode_keeps_template_reload_with_compiled_assets():
    # Arrange
    middleware = SandboxAwareBrowserReloadMiddleware(lambda request: response())
    # Act
    result = middleware(RequestFactory().get("/"))
    # Assert
    assert b"reload-listener" in result.content
