#!/bin/bash
# -*- coding: utf-8 -*-
# Cleanup script for expired anonymous sessions
# Run daily via cron: 0 2 * * * /home/ywatanabe/proj/scitex-cloud/deployment/server/cleanup_anonymous_sessions.sh

set -e

# Project directory
PROJECT_DIR="/home/ywatanabe/proj/scitex-cloud"
cd "$PROJECT_DIR"

# Activate virtual environment
source .venv/bin/activate

# Run cleanup via Django shell
python << EOF
import os
import django

os.environ.setdefault('SCITEX_CLOUD_DJANGO_SETTINGS_MODULE', 'config.settings.settings_prod')
django.setup()

from apps.workspace_app.anonymous_storage import cleanup_expired_sessions
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

logger.info("Starting anonymous session cleanup...")
cleaned, errors = cleanup_expired_sessions()
logger.info(f"Cleanup complete: {cleaned} sessions removed, {errors} errors")
EOF

echo "[$(date)] Anonymous session cleanup completed"

# EOF
