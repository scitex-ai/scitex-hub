"""
Django settings auto-loader for SciTeX Hub.

This module automatically loads the appropriate settings based on:
1. SCITEX_HUB_DJANGO_SETTINGS_MODULE environment variable
2. SCITEX_HUB_ENV environment variable
3. Default to development if not specified

Supported environments:
    Development: export SCITEX_HUB_ENV=development (or dev, leave unset)
    Staging:     export SCITEX_HUB_ENV=staging (or stag)
    Production:  export SCITEX_HUB_ENV=prod (or production)
"""

import os
import sys

# Determine which settings to use
env = os.environ.get("SCITEX_HUB_ENV", "development").lower()

if env in ("prod", "production"):
    from .settings_prod import *
elif env in ("staging", "stag"):
    from .settings_staging import *
elif env in ("development", "dev"):
    from .settings_dev import *
else:
    # Fallback to development
    print(f"    Warning: Unknown SCITEX_HUB_ENV '{env}', defaulting to development")
    from .settings_dev import *
