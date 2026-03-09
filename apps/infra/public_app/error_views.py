#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Error handlers for the public app."""

from django.shortcuts import render
from django.http import HttpResponse


def handler404(request, exception=None):
    """Custom 404 handler that renders the 404.html template."""
    try:
        return render(request, "404.html", status=404)
    except Exception:
        # Fallback if template rendering fails
        html = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Page Not Found</title>
            <style>
                body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
                div { max-width: 600px; margin: 60px auto; padding: 0 16px; text-align: center; }
                h1 { font-size: 48px; }
                p { color: #666; }
            </style>
        </head>
        <body>
            <div>
                <h1>404</h1>
                <h2>Page Not Found</h2>
                <p>The page you're looking for doesn't exist or has been removed.</p>
                <p><a href="/">Go Home</a></p>
            </div>
        </body>
        </html>
        """
        return HttpResponse(html, status=404)


# EOF
