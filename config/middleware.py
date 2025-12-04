#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Custom middleware for SciTeX Cloud.
"""

from django.conf import settings


class JSNoCacheMiddleware:
    """
    Middleware to prevent browser caching of JS files in development.

    This is needed because ES modules are cached by the browser's module map
    independently of HTTP cache headers. Adding no-store ensures fresh fetches.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        # Only apply in development (DEBUG mode)
        if settings.DEBUG:
            # Check if this is a JS file request
            path = request.path.lower()
            if path.endswith('.js') and '/static/' in path:
                # Prevent ALL caching of JS files
                response['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
                response['Pragma'] = 'no-cache'
                response['Expires'] = '0'

        return response
