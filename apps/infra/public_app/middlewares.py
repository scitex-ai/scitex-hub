"""Request-scoped middleware for public_app.

Currently: pin the UI language to English for anonymous visitors who have not
explicitly chosen one, while still honoring the ``django_language`` cookie set
by the footer language switcher.

Why this exists (operator task 2026-09-11): stock ``LocaleMiddleware`` resolves
the request language as session → ``Accept-Language`` → ``LANGUAGE_CODE``, so a
browser advertising ``Accept-Language: ja`` silently rendered the whole landing
in Japanese even though the operator wants English by default and Japanese only
after an explicit selection. This middleware runs BEFORE ``LocaleMiddleware``
and removes the ``Accept-Language`` header whenever the visitor has no
explicit ``django_language`` cookie, forcing the resolution to fall through to
``LANGUAGE_CODE`` (English). A visitor who clicks 日本語 in the footer gets the
cookie and keeps Japanese across subsequent requests.
"""

from __future__ import annotations

from django.http import HttpRequest, HttpResponse

DEFAULT_LANGUAGE = "en"
LANGUAGE_COOKIE = "django_language"


class EnglishDefaultLanguageMiddleware:
    """Pin to English until the user explicitly picks a language."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        chosen = request.COOKIES.get(LANGUAGE_COOKIE)
        if not (chosen and chosen != DEFAULT_LANGUAGE):
            # No explicit non-English choice: strip the browser preference so
            # LocaleMiddleware falls back to LANGUAGE_CODE (English) instead of
            # auto-selecting from Accept-Language.
            request.META["HTTP_ACCEPT_LANGUAGE"] = ""
        return self.get_response(request)
