#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Custom middleware for SciTeX Hub.
"""

from django.conf import settings


class DevNoCacheMiddleware:
    """
    Middleware to prevent browser caching in development.

    Applies to:
    - JS static files (ES modules cached by browser's module map)
    - HTML responses (Django template changes need immediate visibility)
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        # Only apply in development (DEBUG mode)
        if settings.DEBUG:
            path = request.path.lower()
            content_type = response.get("Content-Type", "")

            # JS static files: prevent all caching
            if path.endswith(".js") and "/static/" in path:
                response["Cache-Control"] = (
                    "no-store, no-cache, must-revalidate, max-age=0"
                )
                response["Pragma"] = "no-cache"
                response["Expires"] = "0"
            # HTML responses: revalidate on every request
            elif "text/html" in content_type:
                response["Cache-Control"] = "no-cache, must-revalidate, max-age=0"
                response["Pragma"] = "no-cache"

        return response


# EOF
