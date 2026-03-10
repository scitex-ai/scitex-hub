#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Workflows Feature Views

Exports all workflow-related views.
"""

from .detail import workflow_detail
from .editor import workflow_create, workflow_edit
from .runs import workflow_run_detail, workflow_trigger, workflow_enable_disable
from .delete import workflow_delete

__all__ = [
    "workflow_detail",
    "workflow_create",
    "workflow_edit",
    "workflow_run_detail",
    "workflow_trigger",
    "workflow_enable_disable",
    "workflow_delete",
]
