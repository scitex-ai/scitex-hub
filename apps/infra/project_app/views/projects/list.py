#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Project List View

Display list of user's projects.
"""

from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required


@login_required
def project_list(request):
    """Redirect to user's personal project page (GitHub-style)"""
    return redirect(f"/{request.user.username}/?tab=repositories")


# EOF
