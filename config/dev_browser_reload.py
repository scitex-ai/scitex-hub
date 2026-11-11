"""Inject live-development reload only into eligible development responses."""

from django.conf import settings
from django_browser_reload.middleware import BrowserReloadMiddleware


class SandboxAwareBrowserReloadMiddleware(BrowserReloadMiddleware):
    """Respect baked artifact mode and the response's CSP sandbox declaration."""

    def maybe_inject(self, request, response):
        if getattr(settings, "SCITEX_HUB_FRONTEND_MODE", "build") == "baked":
            return
        policy = response.headers.get("Content-Security-Policy", "")
        for directive in policy.split(";"):
            tokens = directive.lower().split()
            if tokens and tokens[0] == "sandbox" and "allow-same-origin" not in tokens:
                return
        return super().maybe_inject(request, response)
