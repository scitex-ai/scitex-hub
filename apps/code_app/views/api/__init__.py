#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Notebook API views - modular structure."""

from .base import NotebookAPIView
from .list import NotebookListAPI
from .detail import NotebookDetailAPI
from .execution import NotebookExecutionAPI
from .conversion import NotebookConversionAPI
from .sharing import NotebookSharingAPI
from .templates import NotebookTemplatesAPI
from .utilities import notebook_status_api, duplicate_notebook_api

__all__ = [
    "NotebookAPIView",
    "NotebookListAPI",
    "NotebookDetailAPI",
    "NotebookExecutionAPI",
    "NotebookConversionAPI",
    "NotebookSharingAPI",
    "NotebookTemplatesAPI",
    "notebook_status_api",
    "duplicate_notebook_api",
]

# EOF
