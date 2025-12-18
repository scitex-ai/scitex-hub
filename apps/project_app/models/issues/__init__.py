"""
Issues Module - Issue Tracking Models

Exports all models for backward compatibility:
    from apps.project_app.models.issues import Issue, IssueComment, ...
"""

from .issue import Issue, IssueComment
from .metadata import IssueLabel, IssueMilestone
from .tracking import IssueAssignment, IssueEvent

__all__ = [
    # issue.py
    "Issue",
    "IssueComment",
    # metadata.py
    "IssueLabel",
    "IssueMilestone",
    # tracking.py
    "IssueAssignment",
    "IssueEvent",
]
