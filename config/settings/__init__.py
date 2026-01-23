"""
Django settings auto-loader for SciTeX Cloud.

This module automatically loads the appropriate settings based on:
1. SCITEX_CLOUD_DJANGO_SETTINGS_MODULE environment variable
2. SCITEX_CLOUD_ENV environment variable
3. Default to development if not specified

Supported environments:
    Development: export SCITEX_CLOUD_ENV=development (or leave unset)
    NAS:         export SCITEX_CLOUD_ENV=nas
"""

import os
import sys

# Determine which settings to use
env = os.environ.get('SCITEX_CLOUD_ENV', 'development').lower()

if env == 'nas':
    from .settings_nas import *
elif env in ('development', 'dev'):
    from .settings_dev import *
else:
    # Fallback to development
    print(f"    Warning: Unknown SCITEX_CLOUD_ENV '{env}', defaulting to development")
    from .settings_dev import *
