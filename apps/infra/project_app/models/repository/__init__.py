"""
Repository Models Package

Modularized structure:
- project.py: Core Project model with fields only
- project_methods.py: General instance methods
- project_gitea_methods.py: Gitea integration methods
- project_scitex_methods.py: SciTeX integration methods
- project_managers.py: Custom managers and querysets
- project_signals.py: Signal handlers
"""

from .project import Project, ProjectMembership

__all__ = ["Project", "ProjectMembership"]
