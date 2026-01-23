#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Constants and Celery setup for indexer tasks."""

try:
    from celery import shared_task
    CELERY_AVAILABLE = True
except ImportError:
    # Celery not available - use direct function calls
    CELERY_AVAILABLE = False

    def shared_task(func):
        """Decorator stub when Celery is not available"""
        return func


# Supported file extensions
SUPPORTED_FIGURE_EXTENSIONS = {
    '.png', '.jpg', '.jpeg', '.pdf', '.tiff', '.tif', '.svg', '.pptx', '.mmd'
}
SUPPORTED_TABLE_EXTENSIONS = {'.csv', '.xlsx', '.xls', '.tsv', '.ods'}


# EOF
