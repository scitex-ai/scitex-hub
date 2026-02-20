#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from django.urls import path

from apps.unified_app.views.index import unified_content, unified_index

urlpatterns = [
    path("", unified_index, name="unified_index"),
    path("content/<str:module>/", unified_content, name="unified_content"),
    path("<str:module>/", unified_index, name="unified_module"),
]

# EOF
