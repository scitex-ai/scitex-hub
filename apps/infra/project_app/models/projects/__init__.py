"""
Projects module - Project collaboration models (watch, star, fork, invitation)
"""

from .collaboration import (
    ProjectWatch,
    ProjectStar,
    ProjectFork,
    ProjectInvitation,
)

__all__ = [
    "ProjectWatch",
    "ProjectStar",
    "ProjectFork",
    "ProjectInvitation",
]
