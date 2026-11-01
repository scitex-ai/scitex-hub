"""Origin-only policy for the authenticated Writer compatibility adapter.

The leaf separately validates project access and CSRF. This adapter retains
its existing origin gate and delegates trusted-origin interpretation to Django.
"""

from django.middleware.csrf import CsrfViewMiddleware


_SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS", "TRACE"})


def is_cross_origin_write(request):
    # Browsers always send Origin on a cross-site POST; a missing header means
    # a non-browser client, which cannot ride the victim's session anyway.
    if request.method in _SAFE_METHODS:
        return False
    origin = request.headers.get("Origin")
    if origin is None:
        return False
    # Validate Host as before; arbitrary forwarded headers grant no trust.
    request.get_host()
    # Django owns CSRF_TRUSTED_ORIGINS semantics, including scheme-bound
    # wildcard subdomains. Literal membership rejected legitimate HTTPS dev
    # tunnel origins configured as https://*.scitex.ai before compilation.
    # Its origin check also honors only the configured trusted proxy header.
    return not CsrfViewMiddleware(lambda req: None)._origin_verified(request)


