"""Branch and merge operations."""

from typing import Optional, Tuple, Dict
from django.utils import timezone
from django.contrib.auth.models import User
from ...models import (
    Manuscript,
    ManuscriptVersion,
    ManuscriptBranch,
    MergeRequest,
)
from .version_operations import VersionOperations


class BranchOperations:
    """Manage branch creation, merging, and conflict detection."""

    def __init__(self):
        self.version_ops = VersionOperations()

    def create_branch(
        self,
        manuscript: Manuscript,
        branch_name: str,
        description: str,
        user: User,
        base_version: Optional[ManuscriptVersion] = None,
    ) -> ManuscriptBranch:
        """Create a new branch from base version."""

        if not base_version:
            base_version = manuscript.versions.filter(branch_name="main").first()

        branch = ManuscriptBranch.objects.create(
            manuscript=manuscript,
            name=branch_name,
            description=description,
            created_by=user,
            base_version=base_version,
        )

        # Create initial version in new branch
        if base_version:
            self.version_ops.create_version(
                manuscript=manuscript,
                user=user,
                commit_message=f"Created branch '{branch_name}' from {base_version.version_number}",
                branch_name=branch_name,
            )

        return branch

    def create_merge_request(
        self,
        source_branch: ManuscriptBranch,
        target_branch: ManuscriptBranch,
        title: str,
        description: str,
        user: User,
    ) -> MergeRequest:
        """Create a merge request between branches."""

        source_version = source_branch.get_latest_version()
        target_version = target_branch.get_latest_version()

        if not source_version or not target_version:
            raise ValueError("Both branches must have at least one version")

        # Check for conflicts
        has_conflicts, conflict_data = self.check_merge_conflicts(
            source_version, target_version
        )

        merge_request = MergeRequest.objects.create(
            manuscript=source_branch.manuscript,
            title=title,
            description=description,
            source_branch=source_branch,
            target_branch=target_branch,
            source_version=source_version,
            target_version=target_version,
            created_by=user,
            has_conflicts=has_conflicts,
            conflict_data=conflict_data,
            auto_mergeable=not has_conflicts,
        )

        return merge_request

    def merge_branches(
        self, merge_request: MergeRequest, user: User
    ) -> ManuscriptVersion:
        """Merge source branch into target branch."""

        if not merge_request.can_auto_merge():
            raise ValueError("Merge request cannot be auto-merged due to conflicts")

        # Create merge commit
        merge_version = self.version_ops.create_version(
            manuscript=merge_request.manuscript,
            user=user,
            commit_message=f"Merge '{merge_request.source_branch.name}' into '{merge_request.target_branch.name}'",
            branch_name=merge_request.target_branch.name,
            is_major=False,
        )

        # Update merge request
        merge_request.status = "merged"
        merge_request.merged_at = timezone.now()
        merge_request.merged_by = user
        merge_request.merge_commit = merge_version
        merge_request.save()

        # Update source branch
        merge_request.source_branch.is_merged = True
        merge_request.source_branch.merged_at = timezone.now()
        merge_request.source_branch.merged_by = user
        merge_request.source_branch.save()

        return merge_version

    def check_merge_conflicts(
        self, source_version: ManuscriptVersion, target_version: ManuscriptVersion
    ) -> Tuple[bool, Dict]:
        """Check for merge conflicts between versions."""

        # Simple conflict detection based on section modifications
        conflicts = []
        source_sections = source_version.section_contents
        target_sections = target_version.section_contents

        for section_type in set(source_sections.keys()) | set(target_sections.keys()):
            source_content = source_sections.get(section_type, {}).get("content", "")
            target_content = target_sections.get(section_type, {}).get("content", "")

            if source_content != target_content:
                # Check if both branches modified the same section
                base_version = source_version.parent_version
                if base_version:
                    base_content = base_version.section_contents.get(
                        section_type, {}
                    ).get("content", "")

                    if (
                        source_content != base_content
                        and target_content != base_content
                        and source_content != target_content
                    ):
                        conflicts.append(
                            {
                                "section": section_type,
                                "type": "content_conflict",
                                "source_content": source_content,
                                "target_content": target_content,
                                "base_content": base_content,
                            }
                        )

        return len(conflicts) > 0, {"conflicts": conflicts}


# EOF
