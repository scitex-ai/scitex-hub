#!/usr/bin/env python3
"""Configuration for CrossRef Local API"""

import os
from pathlib import Path

# Database configuration
CROSSREF_DB_PATH = os.getenv("CROSSREF_DB_PATH", "/data/crossref.db")

# Server configuration
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "3333"))
WORKERS = int(os.getenv("WORKERS", "4"))
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# Query limits
MAX_SEARCH_RESULTS = 100
MAX_BATCH_SIZE = 100
MAX_CITATION_DEPTH = 3
DEFAULT_CITATION_LIMIT = 100

# Performance settings
ENABLE_QUERY_CACHE = os.getenv("ENABLE_QUERY_CACHE", "true").lower() == "true"
CACHE_TTL_SECONDS = int(os.getenv("CACHE_TTL_SECONDS", "3600"))

# Validation
def validate_config():
    """Validate configuration"""
    db_path = Path(CROSSREF_DB_PATH)
    if not db_path.exists():
        raise FileNotFoundError(f"Database not found: {CROSSREF_DB_PATH}")
    if not db_path.is_file():
        raise ValueError(f"Database path is not a file: {CROSSREF_DB_PATH}")
    return True
