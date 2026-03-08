#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SEO-related views: robots.txt, sitemap.xml."""

from __future__ import annotations

from django.http import HttpResponse


def robots_txt(request):
    """Serve robots.txt with crawler directives.

    Critical: Disallows /dev/ paths to prevent crawlers from
    triggering test endpoints that can hang the server.
    """
    lines = [
        "User-agent: *",
        "Allow: /",
        "",
        "# Block development and internal paths",
        "Disallow: /dev/",
        "Disallow: /admin/",
        "Disallow: /api/",
        "Disallow: /_vite_dev_app/",
        "Disallow: /__reload__/",
        "Disallow: /__debug__/",
        "",
        "# Block visitor/temporary paths",
        "Disallow: /visitor-",
        "",
        "# Sitemap location",
        f"Sitemap: {request.build_absolute_uri('/sitemap.xml')}",
    ]
    return HttpResponse("\n".join(lines), content_type="text/plain")


# EOF
