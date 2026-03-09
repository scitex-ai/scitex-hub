"""Version creation and rollback operations."""

from typing import Optional
from datetime import timedelta
from django.utils import timezone
from django.contrib.auth.models import User
from ...models import Manuscript, ManuscriptVersion, DiffResult
from .diff_generators import DiffEngine
from .diff_utils import DiffUtils


class VersionOperations:
    """Manage manuscript version operations."""

    def __init__(self):
        self.diff_engine = DiffEngine()
        self.diff_utils = DiffUtils()

    def create_version(
        self,
        manuscript: Manuscript,
        user: User,
        commit_message: str = "",
        version_tag: str = "",
        branch_name: str = "main",
        is_major: bool = False,
    ) -> ManuscriptVersion:
        """Create a new version of the manuscript."""

        # Generate version number
        latest_version = manuscript.versions.filter(branch_name=branch_name).first()
        if latest_version:
            # Parse version number and increment
            version_parts = latest_version.version_number.split(".")
            if is_major:
                version_number = f"{int(version_parts[0]) + 1}.0"
            else:
                minor = int(version_parts[1]) if len(version_parts) > 1 else 0
                version_number = f"{version_parts[0]}.{minor + 1}"
        else:
            version_number = "1.0" if is_major else "0.1"

        # Collect current manuscript state
        sections = manuscript.sections.all()
        section_contents = {}
        total_word_count = 0

        for section in sections:
            section_contents[section.section_type] = {
                "title": section.title,
                "content": section.content,
                "word_count": len(section.content.split()),
                "order": section.order,
            }
            total_word_count += len(section.content.split())

        manuscript_data = {
            "title": manuscript.title,
            "abstract": manuscript.abstract,
            "status": manuscript.status,
            "target_journal": manuscript.target_journal,
            "keywords": manuscript.keywords,
            "word_count_total": total_word_count,
            "created_at": manuscript.created_at.isoformat(),
            "updated_at": manuscript.updated_at.isoformat(),
        }

        # Calculate changes from previous version
        changes_count = 0
        word_delta = 0
        lines_added = 0
        lines_removed = 0

        if latest_version:
            # Calculate diff statistics
            old_content = self.diff_utils.reconstruct_content(
                latest_version.section_contents
            )
            new_content = self.diff_utils.reconstruct_content(section_contents)

            diff_result = self.diff_engine.generate_unified_diff(
                old_content, new_content
            )
            changes_count = len(diff_result["changes"])
            word_delta = total_word_count - latest_version.manuscript_data.get(
                "word_count_total", 0
            )
            lines_added = diff_result["stats"]["additions"]
            lines_removed = diff_result["stats"]["deletions"]

        # Create version
        version = ManuscriptVersion.objects.create(
            manuscript=manuscript,
            version_number=version_number,
            version_tag=version_tag,
            branch_name=branch_name,
            created_by=user,
            commit_message=commit_message,
            manuscript_data=manuscript_data,
            section_contents=section_contents,
            parent_version=latest_version,
            is_major_version=is_major,
            total_changes=changes_count,
            word_count_delta=word_delta,
            lines_added=lines_added,
            lines_removed=lines_removed,
        )

        # Update manuscript version counter
        manuscript.version += 1
        manuscript.save()

        return version

    def generate_diff(
        self,
        from_version: ManuscriptVersion,
        to_version: ManuscriptVersion,
        diff_type: str = "unified",
    ) -> DiffResult:
        """Generate diff between two versions."""

        # Check for cached diff
        cached_diff = DiffResult.objects.filter(
            from_version=from_version, to_version=to_version, diff_type=diff_type
        ).first()

        if cached_diff and cached_diff.is_valid_cache():
            return cached_diff

        # Generate new diff
        from_content = self.diff_utils.reconstruct_content(
            from_version.section_contents
        )
        to_content = self.diff_utils.reconstruct_content(to_version.section_contents)

        if diff_type == "unified":
            diff_data = self.diff_engine.generate_unified_diff(from_content, to_content)
        elif diff_type == "side_by_side":
            diff_data = self.diff_engine.generate_side_by_side_diff(
                from_content, to_content
            )
        elif diff_type == "word_level":
            diff_data = self.diff_engine.generate_word_level_diff(
                from_content, to_content
            )
        elif diff_type == "semantic":
            diff_data = self.diff_engine.generate_semantic_diff(
                from_content, to_content
            )
        else:
            raise ValueError(f"Unsupported diff type: {diff_type}")

        # Generate HTML representation
        diff_html = self.diff_utils.generate_diff_html(diff_data)

        # Cache the result
        cache_expires = timezone.now() + timedelta(hours=24)

        diff_result = DiffResult.objects.create(
            manuscript=from_version.manuscript,
            from_version=from_version,
            to_version=to_version,
            diff_type=diff_type,
            diff_data=diff_data,
            diff_html=diff_html,
            diff_stats=diff_data.get("stats", {}),
            cache_expires=cache_expires,
        )

        return diff_result

    def rollback_to_version(
        self, manuscript: Manuscript, target_version: ManuscriptVersion, user: User
    ) -> ManuscriptVersion:
        """Rollback manuscript to a specific version."""

        # Create rollback version with target content
        rollback_version = ManuscriptVersion.objects.create(
            manuscript=manuscript,
            version_number=f"{target_version.version_number}-rollback",
            version_tag=f"Rollback to {target_version.version_number}",
            branch_name=target_version.branch_name,
            created_by=user,
            commit_message=f"Rollback to version {target_version.version_number}",
            manuscript_data=target_version.manuscript_data,
            section_contents=target_version.section_contents,
            parent_version=manuscript.versions.first(),
        )

        # Update manuscript sections with rollback content
        for section_type, section_data in target_version.section_contents.items():
            section, created = manuscript.sections.get_or_create(
                section_type=section_type,
                defaults={
                    "title": section_data["title"],
                    "content": section_data["content"],
                    "order": section_data["order"],
                },
            )
            if not created:
                section.title = section_data["title"]
                section.content = section_data["content"]
                section.order = section_data["order"]
                section.save()

        return rollback_version


# EOF
