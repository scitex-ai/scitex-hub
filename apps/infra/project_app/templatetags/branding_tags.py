#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Branding template tags.

Usage in templates:
    {% load branding_tags %}
    <title>{% page_title %}</title>

Thin adapter ONLY: every rule about how a tab is spelled -- the app names,
the brand suffix, the environment / standalone marker -- lives in pure Python
in ``config/branding.py`` (and is unit-tested there). This tag just reads the
template context and delegates, so the policy stays testable without a
template renderer and can later be lifted into a shared SciTeX package.
"""

from django import template
from django.conf import settings

from config import branding

register = template.Library()


def _detail_from_context(context):
    """Extract the page-level detail (project slug / username), or None.

    Precedence:
      1. ``page_title_detail`` -- an explicit per-view override. A view that
         wants "Account Settings · ... — SciTeX" puts the detail in its context
         rather than writing its own <title>, so the brand suffix is still
         appended exactly once, by the policy, in one place.
      2. ``current_project`` / ``project`` -- the workspace project's slug.
      3. ``profile_user`` -- the username on a profile page.
    """
    explicit = context.get("page_title_detail")
    if explicit:
        return explicit

    for key in ("current_project", "project"):
        obj = context.get(key)
        slug = getattr(obj, "slug", None)
        if slug:
            return slug

    profile_user = context.get("profile_user")
    username = getattr(profile_user, "username", None)
    if username:
        return username

    return None


@register.simple_tag(takes_context=True)
def page_title(context):
    """Render the browser tab title for the current page.

    Pattern (see ``config.branding.page_title``):
        ``<Detail> · <App> — SciTeX``            hub, production
        ``<App> — SciTeX (dev|staging)``         hub, non-production
        ``<App> — SciTeX (standalone)``          standalone app
    """
    request = context.get("request")
    path = getattr(request, "path", "") or ""

    return branding.page_title(
        app=branding.app_for_path(path),
        detail=_detail_from_context(context),
        env=settings.SCITEX_ENV,
        mode=settings.SCITEX_APP_MODE,
    )
