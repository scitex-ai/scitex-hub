#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Journal app URLs: the LEAF is the whole user path (/apps/agentic-journal/).

Login-gated wrapper in journal_django.py; fail-closed 404 when the leaf
is missing or ungateable.
"""

from __future__ import annotations

from .journal_django import urlpatterns as journal_django_patterns

urlpatterns = journal_django_patterns

# EOF
