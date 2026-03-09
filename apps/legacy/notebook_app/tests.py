#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Notebook module tests — validates registration and platform service integration.

Run: pytest apps/notebook_app/tests.py
"""

from django.test import TestCase

from apps.infra.workspace_app.registry import ModuleTestMixin


class NotebookModuleTest(ModuleTestMixin, TestCase):
    """Validates notebook module is properly registered and functional."""

    module_name = "notebook"


# EOF
