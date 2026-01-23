#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Project Detail Redirect View

Handle backward compatibility redirects for old URL patterns.
"""

from django.shortcuts import redirect, get_object_or_404
from django.contrib.auth.decorators import login_required

from ...models import Project


@login_required
def project_detail_redirect(request, pk=None, slug=None):
    """Redirect old URLs to new username/project URLs for backward compatibility"""
    if pk:
        # Redirect from /projects/id/123/ to /username/project-name/
        project = get_object_or_404(Project, pk=pk, owner=request.user)
        return redirect(
            "project_app:detail",
            username=project.owner.username,
            slug=project.slug,
            permanent=True,
        )
    elif slug:
        # Redirect from /projects/project-name/ to /username/project-name/
        project = get_object_or_404(Project, slug=slug, owner=request.user)
        return redirect(
            "project_app:detail",
            username=project.owner.username,
            slug=project.slug,
            permanent=True,
        )
    else:
        return redirect("project_app:list")


# EOF
