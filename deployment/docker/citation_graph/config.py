#!/usr/bin/env python3
"""Configuration for Citation Graph API"""

import os
from pathlib import Path

# Server configuration
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "3334"))
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# Database configuration
CROSSREF_DB_PATH = os.getenv(
    "CROSSREF_DB_PATH",
    "/home/ywatanabe/proj/crossref_local/data/crossref.db"
)

# Citation graph parameters
DEFAULT_TOP_N = 20
MAX_TOP_N = 100
DEFAULT_WEIGHT_COUPLING = 2.0
DEFAULT_WEIGHT_COCITATION = 2.0
DEFAULT_WEIGHT_DIRECT = 1.0

# Cache configuration
CACHE_TTL_SECONDS = int(os.getenv("CACHE_TTL_SECONDS", "3600"))  # 1 hour
CACHE_ENABLED = os.getenv("CACHE_ENABLED", "true").lower() == "true"
CACHE_MAX_SIZE = int(os.getenv("CACHE_MAX_SIZE", "1000"))

# Rate limiting
RATE_LIMIT_ENABLED = os.getenv("RATE_LIMIT_ENABLED", "true").lower() == "true"
RATE_LIMIT_PER_MINUTE = int(os.getenv("RATE_LIMIT_PER_MINUTE", "10"))

# CORS configuration
CORS_ENABLED = os.getenv("CORS_ENABLED", "true").lower() == "true"
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*").split(",")


def validate_config():
    """Validate configuration at startup"""
    errors = []

    # Check database path
    if not Path(CROSSREF_DB_PATH).exists():
        errors.append(f"Database not found: {CROSSREF_DB_PATH}")

    # Check parameters
    if DEFAULT_TOP_N > MAX_TOP_N:
        errors.append(f"DEFAULT_TOP_N ({DEFAULT_TOP_N}) cannot exceed MAX_TOP_N ({MAX_TOP_N})")

    if errors:
        raise ValueError(f"Configuration errors:\n" + "\n".join(f"  - {e}" for e in errors))

    return True
