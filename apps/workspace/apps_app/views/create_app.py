#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Home "+ Create app" tile target: a placeholder until agent-built apps ship."""

from django.shortcuts import render


def create_app_placeholder(request):
    return render(request, "apps_app/create_app_placeholder.html")


# EOF
