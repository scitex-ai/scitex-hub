# Central import file for accessing models from modular apps
# This allows backward compatibility while maintaining modular architecture

# Auth models
try:
    from apps.infra.auth_app.models import UserProfile, EmailVerification
    from apps.infra.auth_app.models import (
        is_japanese_academic_email,
        JAPANESE_ACADEMIC_DOMAINS,
    )
except ImportError:
    # Fallback for development/test environments
    UserProfile = None
    EmailVerification = None
    is_japanese_academic_email = None
    JAPANESE_ACADEMIC_DOMAINS = []

# Project models
try:
    from apps.infra.project_app.models import (
        Project,
        ProjectMembership,
        Organization,
        ResearchGroup,
        ResearchGroupMembership,
        ProjectPermission,
    )
except ImportError:
    Project = None
    ProjectMembership = None
    Organization = None
    ResearchGroup = None
    ResearchGroupMembership = None
    ProjectPermission = None

# Export all models for easy importing
__all__ = [
    "UserProfile",
    "EmailVerification",
    "is_japanese_academic_email",
    "JAPANESE_ACADEMIC_DOMAINS",
    "Project",
    "ProjectMembership",
    "Organization",
    "ResearchGroup",
    "ResearchGroupMembership",
    "ProjectPermission",
]
