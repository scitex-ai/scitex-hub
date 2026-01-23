"""
DOI service exception classes.
Defines exceptions for DOI-related errors in the repository service layer.
"""


class DOIServiceError(Exception):
    """Base exception for DOI service errors"""

    pass


class DOIMetadataError(DOIServiceError):
    """DOI metadata related errors"""

    pass


class DOIAssignmentError(DOIServiceError):
    """DOI assignment related errors"""

    pass
