"""
ExternalAPI proxy service for user apps.

Provides a centralized HTTP proxy with rate limiting and method allow-listing,
so user apps can call external services safely through the platform.
"""

from .proxy import ExternalAPIProxy
from .registry import get_api, list_apis, register_api

__all__ = [
    "ExternalAPIProxy",
    "register_api",
    "get_api",
    "list_apis",
]

# EOF
