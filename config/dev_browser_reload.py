"""Keep the development reload worker out of opaque-origin sandbox responses."""

from django_browser_reload.middleware import BrowserReloadMiddleware


class SandboxAwareBrowserReloadMiddleware(BrowserReloadMiddleware):
    """Respect the response's standard CSP sandbox declaration."""

    def maybe_inject(self, request, response):
        policy = response.headers.get("Content-Security-Policy", "")
        for directive in policy.split(";"):
            tokens = directive.lower().split()
            if tokens and tokens[0] == "sandbox" and "allow-same-origin" not in tokens:
                return
        return super().maybe_inject(request, response)
