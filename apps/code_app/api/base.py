#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Timestamp: "2025-11-04 20:30:42 (ywatanabe)"
# File: /home/ywatanabe/proj/scitex-cloud/apps/code_app/api_views.py
# ----------------------------------------
from __future__ import annotations
import os

__FILE__ = "./apps/code_app/api_views.py"
__DIR__ = os.path.dirname(__FILE__)
# ----------------------------------------

"""
API views for SciTeX-Code Jupyter notebook integration.
"""

import json
import logging
import threading
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views import View
from rest_framework.decorators import api_view
from rest_framework.decorators import permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from .models import Notebook
from .models import CodeExecutionJob
from .jupyter import NotebookManager
from .jupyter import NotebookExecutor
from .jupyter import NotebookConverter
from .jupyter import NotebookTemplates
from .jupyter import NotebookValidator

logger = logging.getLogger(__name__)


@method_decorator(login_required, name="dispatch")
class NotebookAPIView(View):
    """Base API view for notebook operations."""

    def get_notebook_manager(self):
        return NotebookManager(self.request.user)



# EOF
