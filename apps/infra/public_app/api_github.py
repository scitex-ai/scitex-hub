"""Anonymous public metadata endpoint; no auth/session/model or user state access."""

from django.core.cache import caches
from django.http import JsonResponse
from django.views.decorators.http import require_GET

from .services.landing_github_live import bootstrap_counts, cached_counts


@require_GET
def github_counts(request):
    """Return only fixed public-repository counts, ignoring client query selectors."""
    backend = caches["default"]
    # A disabled or database cache cannot provide the required shared quota gate.
    supported = backend.__class__.__module__ in {
        "django.core.cache.backends.redis",
        "django.core.cache.backends.locmem",
        "django_redis.cache",
    }
    payload = cached_counts(backend) if supported else bootstrap_counts()
    response = JsonResponse(payload)
    response["Cache-Control"] = "public, max-age=30"
    return response
