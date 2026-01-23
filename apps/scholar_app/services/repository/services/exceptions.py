"""Repository service exceptions."""


class RepositoryServiceError(Exception):
    """Base exception for repository service errors"""
    pass


class AuthenticationError(RepositoryServiceError):
    """Authentication-related errors"""
    pass


class APIError(RepositoryServiceError):
    """API-related errors"""
    pass


class ValidationError(RepositoryServiceError):
    """Data validation errors"""
    pass


# EOF
