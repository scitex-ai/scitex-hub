#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Version Control System for SciTeX Writer - modular structure."""

from .diff_generators import DiffEngine
from .diff_utils import DiffUtils
from .version_operations import VersionOperations
from .branch_operations import BranchOperations


class VersionControlManager:
    """
    Unified interface for version control operations.
    
    Provides backward compatibility by aggregating all version control
    functionality into a single manager class.
    """

    def __init__(self):
        self.diff_engine = DiffEngine()
        self.version_ops = VersionOperations()
        self.branch_ops = BranchOperations()

    # Version operations
    def create_version(self, *args, **kwargs):
        """Create a new version of the manuscript."""
        return self.version_ops.create_version(*args, **kwargs)

    def generate_diff(self, *args, **kwargs):
        """Generate diff between two versions."""
        return self.version_ops.generate_diff(*args, **kwargs)

    def rollback_to_version(self, *args, **kwargs):
        """Rollback manuscript to a specific version."""
        return self.version_ops.rollback_to_version(*args, **kwargs)

    # Branch operations
    def create_branch(self, *args, **kwargs):
        """Create a new branch from base version."""
        return self.branch_ops.create_branch(*args, **kwargs)

    def create_merge_request(self, *args, **kwargs):
        """Create a merge request between branches."""
        return self.branch_ops.create_merge_request(*args, **kwargs)

    def merge_branches(self, *args, **kwargs):
        """Merge source branch into target branch."""
        return self.branch_ops.merge_branches(*args, **kwargs)

    # Internal helper methods for backward compatibility
    def _reconstruct_content(self, section_contents):
        """Reconstruct full content from section contents."""
        return self.version_ops.diff_utils.reconstruct_content(section_contents)

    def _generate_diff_html(self, diff_data):
        """Generate HTML representation of diff data."""
        return self.version_ops.diff_utils.generate_diff_html(diff_data)

    def _check_merge_conflicts(self, source_version, target_version):
        """Check for merge conflicts between versions."""
        return self.branch_ops.check_merge_conflicts(source_version, target_version)


__all__ = [
    "DiffEngine",
    "DiffUtils",
    "VersionOperations",
    "BranchOperations",
    "VersionControlManager",
]

# EOF
