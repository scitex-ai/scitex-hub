"""SciTeX-funded chat accounting and provider safety."""

from .errors import (
    ERROR_CATEGORIES,
    ClassifiedProviderError,
    classify_provider_exception,
)

__all__ = [
    "ERROR_CATEGORIES",
    "ClassifiedProviderError",
    "classify_provider_exception",
]
