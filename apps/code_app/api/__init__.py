#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Notebook API views - modular structure."""

from .base import NotebookAPIView
from .list_api import NotebookListAPI
from .detail_api import NotebookDetailAPI
from .execution_api import NotebookExecutionAPI
from .conversion_api import NotebookConversionAPI
from .sharing_api import NotebookSharingAPI
from .templates_api import NotebookTemplatesAPI

__all__ = [
    "NotebookAPIView",
    "NotebookListAPI",
    "NotebookDetailAPI",
    "NotebookExecutionAPI",
    "NotebookConversionAPI",
    "NotebookSharingAPI",
    "NotebookTemplatesAPI",
]

# EOF
