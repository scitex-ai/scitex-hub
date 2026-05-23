#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WSGI config for SciTeX Hub project.

It exposes the WSGI callable as a module-level variable named ``application``.
"""

import os

from django.core.wsgi import get_wsgi_application

# Use SCITEX_HUB_ prefix for configuration
settings_module = os.getenv("SCITEX_HUB_DJANGO_SETTINGS_MODULE") or "config.settings"
os.environ.setdefault("DJANGO_SETTINGS_MODULE", settings_module)

application = get_wsgi_application()
