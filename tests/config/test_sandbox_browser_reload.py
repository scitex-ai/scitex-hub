"""The actual reload middleware respects a standard opaque-origin CSP."""

from django.http import HttpResponse
from django.test import RequestFactory, override_settings
from django.urls import include, path

urlpatterns = [path("__reload__/", include("django_browser_reload.urls"))]
from asgiref.sync import async_to_sync

from config.dev_browser_reload import SandboxAwareBrowserReloadMiddleware


def response(policy=""):
    result = HttpResponse("<html><body>Chart</body></html>")
    if policy:
        result["Content-Security-Policy"] = policy
    return result


@override_settings(DEBUG=True, ROOT_URLCONF=__name__)
def test_opaque_sandbox_does_not_receive_worker():
    for policy in ("sandbox allow-scripts", "default-src 'self'; sandbox"):
        middleware = SandboxAwareBrowserReloadMiddleware(lambda request: response(policy))
        result = middleware(RequestFactory().get("/chart/"))
        assert b"reload-listener" not in result.content
        assert result["Content-Security-Policy"] == policy


@override_settings(DEBUG=True, ROOT_URLCONF=__name__)
def test_regular_and_same_origin_pages_keep_reload():
    for policy in ("", "sandbox allow-scripts allow-same-origin"):
        middleware = SandboxAwareBrowserReloadMiddleware(lambda request: response(policy))
        result = middleware(RequestFactory().get("/"))
        assert b"reload-listener" in result.content


@override_settings(DEBUG=True, ROOT_URLCONF=__name__)
def test_async_sandbox_response_keeps_same_protection():
    async def view(request):
        return response("sandbox allow-scripts")

    middleware = SandboxAwareBrowserReloadMiddleware(view)
    result = async_to_sync(middleware)(RequestFactory().get("/chart/"))
    assert b"reload-listener" not in result.content
