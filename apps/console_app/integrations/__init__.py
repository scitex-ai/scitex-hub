#!/usr/bin/env python3
"""
Integrations package for SciTeX-Code application.
Contains external service integrations.
"""

# Integrations are imported on-demand to avoid circular dependencies
# Import specific integrations as needed using:
# from apps.console_app.integrations.repository_integration import auto_sync_code_completion

__all__ = [
    "repository_integration",
]
