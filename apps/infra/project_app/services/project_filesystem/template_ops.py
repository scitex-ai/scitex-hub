"""
Template Operations Manager Module

Handles template cloning, copying, and customization for projects.
Delegates all business logic to scitex.template.
"""

import logging
from pathlib import Path
from typing import Optional, Tuple

from django.conf import settings

from ...models import Project

logger = logging.getLogger(__name__)


def _project_metadata(project: Project) -> dict:
    """Extract plain metadata dict from a Django Project model."""
    owner = project.owner
    return {
        "name": project.name,
        "description": project.description or "",
        "owner": owner.username if owner else "",
        "owner_full_name": (owner.get_full_name() if owner else "") or "",
        "id": project.id,
        "created_at": (
            project.created_at.strftime("%Y-%m-%d") if project.created_at else ""
        ),
        "updated_at": (
            project.updated_at.strftime("%Y-%m-%d %H:%M:%S")
            if project.updated_at
            else ""
        ),
        "progress": getattr(project, "progress", 0),
        "hypotheses": getattr(project, "hypotheses", "") or "",
    }


class TemplateOperationsManager:
    """Manages template creation and customization for projects."""

    def __init__(self, filesystem_manager):
        self.manager = filesystem_manager

    def create_minimal_readme(self, project: Project, project_path: Path):
        """Create minimal README file for empty projects."""
        from scitex.template import create_minimal_readme

        create_minimal_readme(str(project_path), _project_metadata(project))

    def create_project_readme(self, project: Project, project_path: Path):
        """Create comprehensive README file for the project."""
        from scitex.template import create_project_readme

        create_project_readme(str(project_path), _project_metadata(project))

    def create_project_config_files(self, project: Project, project_path: Path):
        """Create essential configuration files for the project."""
        from scitex.template import (
            create_env_template,
            create_paths_config,
            create_project_config,
        )

        meta = _project_metadata(project)
        create_project_config(str(project_path), meta)
        create_paths_config(str(project_path))
        create_env_template(str(project_path), meta)

    def create_requirements_file(self, project: Project, project_path: Path):
        """Create requirements.txt with essential scientific packages."""
        from scitex.template import create_requirements_file

        create_requirements_file(str(project_path))

    def copy_from_example_template(
        self, project_path: Path, project: Project, template_type: str = "research"
    ) -> bool:
        """Copy template structure from local or remote source."""
        try:
            if project_path.exists() and not getattr(
                project, "_research_template_pending", False
            ):
                logger.info(
                    f"Project path already exists: {project_path}, skipping template"
                )
                return False

            if not project_path.parent.exists():
                project_path.parent.mkdir(parents=True, exist_ok=True)

            from scitex_template import clone_template

            git_strategy = "child" if template_type in ("minimal", "research") else None

            if project_path.exists():
                from .new_repository_template import populate_new_repository

                success = populate_new_repository(
                    project_path,
                    lambda target: clone_template(
                        template_id=template_type,
                        project_dir=str(target),
                        git_strategy=None,
                    ),
                )
            else:
                success = clone_template(
                    template_id=template_type,
                    project_dir=str(project_path),
                    git_strategy=git_strategy,
                )

            if success:
                self._customize_after_clone(project_path, project, template_type)
                logger.info(
                    f"Successfully created {template_type} template at {project_path}"
                )

            return success

        except ImportError as e:
            logger.error(f"scitex package not available: {e}")
            return False
        except Exception as e:
            logger.error(f"Error creating {template_type} project template: {e}")
            return False

    def _customize_after_clone(
        self, project_path: Path, project: Project, template_type: str
    ):
        """Customize template after cloning — delegates to scitex.template."""
        from scitex_template import customize_minimal_template, customize_template

        meta = _project_metadata(project)
        if template_type == "minimal":
            customize_minimal_template(str(project_path), meta)
        else:
            customize_template(str(project_path), meta, template_type)

    def initialize_scitex_writer_template(
        self, project: Project
    ) -> Tuple[bool, Optional[Path]]:
        """Make the project's Writer workspace ready to open and compile.

        Delegates to ``scitex_writer.ensure_workspace`` on the project root.
        That creates a workspace when there is none, and — the research
        template's case — installs the writer engine around a manuscript the
        template shipped in ``.scitex/writer``, adding only what is missing so
        a repeat call never touches the author's text. This used to compute
        the workspace path and only test that it existed, so a project whose
        template shipped no workspace reported "initialization failed" and
        opened as a 404 in Writer (scitex-template#84).
        """
        project_root = self.manager.get_project_root_path(project)
        if project_root is None:
            logger.error(
                "Writer initialization: no directory for project %s", project.pk
            )
            return False, None
        workspace = ensure_writer_workspace(project_root)
        if workspace is None:
            logger.error("Writer workspace not ready for project %s", project.pk)
            return False, None
        return True, workspace


def ensure_writer_workspace(project_root: Path) -> Optional[Path]:
    """Ready the Writer workspace under ``project_root``; ``None`` if it is not.

    ``scitex_writer.ensure_workspace`` creates a missing workspace, or installs
    the engine around a template-shipped manuscript (additive only). The
    template version follows ``SCITEX_WRITER_TEMPLATE_BRANCH`` /
    ``SCITEX_WRITER_TEMPLATE_TAG`` like ``WriterService``. Ready means the
    manuscript directory the Writer opens exists afterwards.
    """
    from apps.infra.project_app.services.writer_workspace_layout import (
        get_manuscript_path,
    )

    def _setting(name):
        value = getattr(settings, name, None)
        return None if value in (None, "", "null") else value

    try:
        from scitex_writer import ensure_workspace

        workspace = Path(
            ensure_workspace(
                project_root,
                git_strategy="parent",
                branch=_setting("SCITEX_WRITER_TEMPLATE_BRANCH"),
                tag=_setting("SCITEX_WRITER_TEMPLATE_TAG"),
            )
        )
    except Exception:
        logger.exception("Writer workspace initialization failed")
        return None
    if not get_manuscript_path(project_root).is_dir():
        return None
    return workspace


# EOF
