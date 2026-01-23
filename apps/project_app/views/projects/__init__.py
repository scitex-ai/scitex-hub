#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Projects Feature Views

Exports all project-related views.
"""

from .list import project_list
from .detail import project_detail
from .detail_redirect import project_detail_redirect
from .create import project_create
from .create_template import project_create_from_template
from .edit import project_edit
from .delete import project_delete
from .settings import project_settings
from .api import (
    api_check_name_availability,
    api_project_list,
    api_project_create,
    api_project_detail,
)

__all__ = [
    "project_list",
    "project_detail",
    "project_detail_redirect",
    "project_create",
    "project_create_from_template",
    "project_edit",
    "project_delete",
    "project_settings",
    "api_check_name_availability",
    "api_project_list",
    "api_project_create",
    "api_project_detail",
]
