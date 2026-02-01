"""
Project App Models
Central export point for all project-related models

Following Django organization best practices:
- Models are split into domain-specific modules
- All models are exported from this __init__.py for backward compatibility
- Existing imports like `from apps.project_app.models import Project` continue to work
"""

# Repository models (Project, ProjectMembership - split from core)
# Core models (ProjectPermission, VisitorAllocation)
from .core import (
    ProjectPermission,
    VisitorAllocation,
)

# Issue models
from .issues import (
    Issue,
    IssueAssignment,
    IssueComment,
    IssueEvent,
    IssueLabel,
    IssueMilestone,
    IssueTemplate,
)

# Collaboration models (Watch, Star, Fork, Invitation)
from .projects import (
    ProjectFork,
    ProjectInvitation,
    ProjectStar,
    ProjectWatch,
)

# Pull Request models
from .pull_requests import (
    PullRequest,
    PullRequestComment,
    PullRequestCommit,
    PullRequestEvent,
    PullRequestLabel,
    PullRequestReview,
)

# Remote project models
from .remote import (
    RemoteCredential,
    RemoteProjectConfig,
)
from .repository import (
    Project,
    ProjectMembership,
)

# Workflow models (CI/CD workflows)
from .workflows import (
    Workflow,
    WorkflowArtifact,
    WorkflowJob,
    WorkflowRun,
    WorkflowSecret,
    WorkflowStep,
)

# Explicit exports for clarity
__all__ = [
    # Core models
    "Project",
    "ProjectMembership",
    "ProjectPermission",
    "VisitorAllocation",
    # Remote project models
    "RemoteCredential",
    "RemoteProjectConfig",
    # Collaboration models
    "ProjectWatch",
    "ProjectStar",
    "ProjectFork",
    "ProjectInvitation",
    # Issue models
    "Issue",
    "IssueComment",
    "IssueLabel",
    "IssueMilestone",
    "IssueAssignment",
    "IssueEvent",
    "IssueTemplate",
    # Pull Request models
    "PullRequest",
    "PullRequestReview",
    "PullRequestComment",
    "PullRequestCommit",
    "PullRequestLabel",
    "PullRequestEvent",
    # Workflow models
    "Workflow",
    "WorkflowRun",
    "WorkflowJob",
    "WorkflowStep",
    "WorkflowSecret",
    "WorkflowArtifact",
]
