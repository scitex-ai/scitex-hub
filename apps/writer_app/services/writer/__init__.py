"""
Writer service module.

Provides WriterService class that wraps scitex.writer.Writer for Django.
Organized into focused modules for maintainability.
"""

from .service import WriterService

__all__ = ["WriterService"]
