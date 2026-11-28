# -*- coding: utf-8 -*-
# File: config/security_views.py
"""Small public endpoints that belong to the site's security posture:

- POST /api/csp-report/          CSP violation sink (logged, never stored)
- GET  /.well-known/security.txt RFC 9116 contact file
- GET  /sitemap.xml              public pages, referenced by robots.txt
"""

from __future__ import annotations

import json
import logging
from xml.sax.saxutils import escape

from django.conf import settings
from django.http import HttpResponse, HttpResponseNotAllowed
from django.urls import NoReverseMatch, reverse
from django.views.decorators.csrf import csrf_exempt

logger = logging.getLogger("scitex_hub.security.csp")

_MAX_REPORT_BYTES = 16 * 1024
_KEPT_FIELDS = (
    "document-uri",
    "documentURL",
    "violated-directive",
    "effective-directive",
    "effectiveDirective",
    "blocked-uri",
    "blockedURL",
    "source-file",
    "sourceFile",
    "line-number",
    "lineNumber",
    "disposition",
)


def _violations(payload):
    """Yield the report bodies of both wire formats.

    report-uri sends ``{"csp-report": {...}}``; the Reporting API (report-to)
    sends ``[{"type": "csp-violation", "body": {...}}, ...]``.
    """
    if isinstance(payload, dict) and isinstance(payload.get("csp-report"), dict):
        yield payload["csp-report"]
    elif isinstance(payload, list):
        for item in payload:
            if isinstance(item, dict) and isinstance(item.get("body"), dict):
                yield item["body"]


@csrf_exempt  # browsers POST reports without a token; the view only logs
def csp_report(request):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    body = request.body[:_MAX_REPORT_BYTES]
    try:
        payload = json.loads(body or b"null")
    except ValueError:
        return HttpResponse(status=400)
    for report in _violations(payload):
        kept = {k: str(report[k])[:300] for k in _KEPT_FIELDS if k in report}
        logger.warning("csp-violation %s", json.dumps(kept, sort_keys=True))
    return HttpResponse(status=204)


def security_txt(request):
    expires = settings.SECURITY_TXT_EXPIRES.strftime("%Y-%m-%dT%H:%M:%SZ")
    lines = [
        f"Contact: {settings.SECURITY_TXT_CONTACT}",
        f"Expires: {expires}",
        f"Preferred-Languages: {settings.SECURITY_TXT_PREFERRED_LANGUAGES}",
        f"Canonical: {settings.SECURITY_TXT_CANONICAL}",
        "",
    ]
    return HttpResponse("\n".join(lines), content_type="text/plain; charset=utf-8")


def sitemap_xml(request):
    base = f"https://{request.get_host()}"
    urls = []
    for name in settings.SITEMAP_URL_NAMES:
        try:
            urls.append(base + reverse(name))
        except NoReverseMatch:
            logger.error("sitemap: URL name %s does not resolve", name)
    body = "\n".join(
        [
            '<?xml version="1.0" encoding="UTF-8"?>',
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
            *(f"  <url><loc>{escape(u)}</loc></url>" for u in urls),
            "</urlset>",
            "",
        ]
    )
    return HttpResponse(body, content_type="application/xml; charset=utf-8")
