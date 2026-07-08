"""
Visitor Workspace Management — guarded, verified reset pipeline.

Security contract (visitor-slot isolation audit 2026-07-07): a visitor
slot may only be handed to a new visitor after its workspace has been
wiped, VERIFIED empty, and re-cloned from the template with the clone
verified. Any failure raises :class:`WorkspaceResetError` so the caller
(slot_lifecycle) quarantines the slot — a failed reset must never be
silently ignored (that was audit gap #1: an unguarded ``rmtree`` aborted
on ``PermissionError('revision.tex')`` AFTER the new Project row was
created, leaving the previous visitor's files for the next one).

Pipeline order (wipe FIRST, create only after verified-clean):
  1. Delete ALL Project rows owned by the visitor (post_delete signal
     best-effort deletes their Gitea repos).
  2. Wipe the visitor's entire filesystem base dir + VERIFY empty.
  3. Hard-delete every Gitea repo still owned by the visitor + VERIFY
     zero repos remain (audit gap #4: a surviving repo at the stable
     path gets adopted by the next visitor's project).
  4. Clear user-scoped DB rows (chat, LLM logs, app installs/stars/
     reviews, dev installs — audit gap #5).
  5. Create the fresh default Project row.
  6. Clone the template + VERIFY the template marker exists.

Uses scitex.template.clone_template() as single source of truth for
templates.
"""

import logging
from pathlib import Path

from django.conf import settings
from django.contrib.auth.models import User

from apps.infra.project_app.models import Project

from .workspace_wipe import WorkspaceWipeError, wipe_directory_contents

logger = logging.getLogger(__name__)

# Single source of truth for the template marker layout (2026-07-08
# incident: this was ``scitex/writer`` — no dot — while the REAL
# ``scitex_template.clone_scitex_minimal`` / ``scitex_writer
# .ensure_workspace`` create dot-prefixed ``.scitex/writer`` +
# ``.scitex/scholar``, so verification never passed and every slot was
# quarantined). Verified against scitex-writer 2.17.5 and 2.26.1.
# tests/apps/project_app/services/visitor_pool/
# test_template_marker_reality.py locks this against the real packages.
TEMPLATE_MARKER_RELPATH = ".scitex/writer"


class WorkspaceResetError(Exception):
    """A visitor workspace reset failed — the slot MUST be quarantined."""


def verify_template_marker(project_path: Path) -> bool:
    """True if the cloned template's marker content is present.

    Marker = ``.scitex/writer/`` (:data:`TEMPLATE_MARKER_RELPATH`)
    exists and is non-empty (same check the pool initializer uses for
    readiness).
    """
    writer_dir = Path(project_path) / TEMPLATE_MARKER_RELPATH
    try:
        return writer_dir.is_dir() and any(writer_dir.iterdir())
    except OSError:
        return False


class WorkspaceManager:
    """Manages visitor workspace lifecycle."""

    VISITOR_USER_PREFIX = "visitor-"
    DEFAULT_PROJECT_SLUG = "default-project"

    @classmethod
    def ensure_manuscript_record(cls, project: Project, project_path: Path):
        """
        Ensure Manuscript DB record exists for a visitor project.

        Called after scitex_minimal template clone which already creates
        .scitex/writer/ with the full writer workspace.

        Args:
            project: Project model instance
            project_path: Path to project root directory
        """
        try:
            writer_dir = Path(project_path) / TEMPLATE_MARKER_RELPATH
            manuscript_dir = writer_dir / "01_manuscript"

            if manuscript_dir.exists():
                from apps.workspace.writer_app.models import Manuscript

                Manuscript.objects.get_or_create(
                    project=project,
                    defaults={
                        "owner": project.owner,
                        "title": f"{project.name} Manuscript",
                    },
                )
                logger.info(
                    f"[VisitorPool] Manuscript record ensured for {project.slug}"
                )
            else:
                logger.warning(
                    f"[VisitorPool] Writer workspace missing 01_manuscript: {writer_dir}"
                )

        except Exception as e:
            logger.error(
                f"[VisitorPool] Failed to ensure manuscript record for {project.slug}: {e}"
            )

    @classmethod
    def reset_visitor_workspace(
        cls, visitor_user: User, *, gitea_client=None, clone_fn=None
    ):
        """
        Reset a visitor's workspace to a verified-clean template state.

        Clears ALL user-generated data to prevent leakage between
        visitors: projects + filesystem, Gitea repos, chat sessions,
        LLM logs, and user-scoped app rows.

        Args:
            visitor_user: The pool visitor whose slot is being recycled.
            gitea_client: Injectable Gitea API client (duck-typed:
                ``list_repositories``/``delete_repository``). ``None``
                constructs the real :class:`GiteaClient` when Gitea is
                configured (``settings.GITEA_TOKEN``).
            clone_fn: Injectable template clone callable with the
                ``scitex.template.clone_template`` signature. ``None``
                uses the real one.

        Raises:
            WorkspaceResetError: on ANY wipe/verify/clone failure. The
                caller must quarantine the slot — never serve it.
        """
        project_slug = cls.DEFAULT_PROJECT_SLUG

        from apps.infra.project_app.services.project_filesystem import (
            get_project_filesystem_manager,
        )

        manager = get_project_filesystem_manager(visitor_user)
        base_path = Path(manager.base_path)

        # 1. Delete ALL projects owned by the visitor (not just the
        #    default one — visitors can create more). post_delete signal
        #    best-effort deletes Gitea repos; step 3 verifies.
        visitor_projects = Project.objects.filter(owner=visitor_user)
        project_count = visitor_projects.count()
        if project_count:
            visitor_projects.delete()
            logger.info(
                f"[VisitorPool] Deleted {project_count} project rows for "
                f"{visitor_user.username}"
            )

        # 2. Wipe FIRST and verify empty (before any create).
        try:
            wipe_directory_contents(base_path)
        except WorkspaceWipeError as exc:
            raise WorkspaceResetError(
                f"Filesystem wipe failed for {visitor_user.username}: {exc}"
            ) from exc

        # 3. Gitea: hard-delete every repo the visitor still owns and
        #    verify zero remain (stable-path repos survive best-effort
        #    signal deletion and would be adopted by the next visitor).
        cls._purge_gitea_repos_verified(visitor_user, gitea_client)

        # 4. Clear user-scoped DB rows (chat, LLM logs, app rows).
        cls._clear_visitor_data(visitor_user)

        # NOTE (container state): Apptainer/container overlay state for
        # visitor users is NOT yet wiped here — scitex-container
        # integration is a follow-up. Tracked on card
        # hub-visitor-slot-isolation-audit (audit gap #6). Do not treat
        # this reset as covering container state.

        # 5.–6. Only now create the fresh Project row + clone template.
        project = Project.objects.create(
            name=project_slug,
            slug=project_slug,
            description="Try SciTeX features - sign up to save permanently!",
            owner=visitor_user,
            visibility="private",
            data_location=f"{visitor_user.username}/{project_slug}",
        )
        cls._initialize_reset_directory(
            visitor_user, project, project_slug, clone_fn=clone_fn
        )
        logger.info(
            f"[VisitorPool] Verified-clean reset complete for {visitor_user.username}"
        )

    @classmethod
    def _purge_gitea_repos_verified(cls, visitor_user: User, gitea_client=None):
        """Delete every Gitea repo owned by the visitor; verify none remain.

        Raises WorkspaceResetError on any failure (including Gitea being
        unreachable) — an unverified repo deletion is a leak channel.
        Skipped only when Gitea is not configured at all in this
        deployment (no token) and no client was injected.
        """
        username = visitor_user.username

        if gitea_client is None:
            if not getattr(settings, "GITEA_TOKEN", ""):
                logger.warning(
                    f"[VisitorPool] Gitea not configured (no token) — skipping "
                    f"repo purge for {username}"
                )
                return
            from apps.infra.gitea_app.api_client import GiteaClient

            try:
                gitea_client = GiteaClient()
            except Exception as exc:
                raise WorkspaceResetError(
                    f"Gitea client init failed for {username}: {exc}"
                ) from exc

        try:
            repos = gitea_client.list_repositories(username)
            for repo in repos:
                repo_name = repo.get("name")
                logger.info(
                    f"[VisitorPool] Hard-deleting Gitea repo {username}/{repo_name}"
                )
                gitea_client.delete_repository(owner=username, repo=repo_name)

            # VERIFY: the visitor must own zero repos now.
            remaining = gitea_client.list_repositories(username)
        except WorkspaceResetError:
            raise
        except Exception as exc:
            raise WorkspaceResetError(
                f"Gitea repo purge failed for {username}: {exc}"
            ) from exc

        if remaining:
            names = [r.get("name") for r in remaining]
            raise WorkspaceResetError(
                f"Gitea repos survived deletion for {username}: {names!r}"
            )

    @classmethod
    def _clear_visitor_data(cls, visitor_user: User):
        """Delete all user-scoped rows for a visitor.

        Covers chat sessions + LLM usage logs (2026-03 fix) AND the
        user-FK app rows the audit found were never cleared (gap #5):
        ModuleInstallation / DevInstallation / ModuleStar / ModuleReview.

        Raises WorkspaceResetError on failure — leftover rows leak the
        previous visitor's activity to the next one.
        """
        try:
            from apps.infra.llm_app.models import ChatSession, LLMUsageLog
            from apps.workspace.apps_app.models import (
                DevInstallation,
                ModuleInstallation,
                ModuleReview,
                ModuleStar,
            )

            chat_count = ChatSession.objects.filter(user=visitor_user).count()
            ChatSession.objects.filter(user=visitor_user).delete()
            # LLMUsageLog has no direct user FK — it hangs off the
            # user's IntegrationConnection. (The pre-audit code filtered
            # on a nonexistent `user` field and swallowed the resulting
            # FieldError, so LLM logs were NEVER actually cleared.)
            LLMUsageLog.objects.filter(connection__user=visitor_user).delete()
            ModuleInstallation.objects.filter(user=visitor_user).delete()
            DevInstallation.objects.filter(user=visitor_user).delete()
            ModuleStar.objects.filter(user=visitor_user).delete()
            ModuleReview.objects.filter(user=visitor_user).delete()
            if chat_count > 0:
                logger.info(
                    f"[VisitorPool] Cleared {chat_count} chat sessions for "
                    f"{visitor_user.username}"
                )
        except WorkspaceResetError:
            raise
        except Exception as exc:
            raise WorkspaceResetError(
                f"Clearing user-scoped rows failed for {visitor_user.username}: {exc}"
            ) from exc

    @classmethod
    def _initialize_reset_directory(
        cls, visitor_user: User, project: Project, project_slug: str, *, clone_fn=None
    ):
        """Clone the template into the (verified-empty) workspace and verify it."""
        from apps.infra.project_app.services.project_filesystem import (
            get_project_filesystem_manager,
        )

        manager = get_project_filesystem_manager(visitor_user)
        project_path = Path(manager.base_path) / project_slug

        from .pool_initialization import VISITOR_TEMPLATE_ID

        # The base dir was verified empty before the Project row was
        # created, but the create_gitea_repository post_save signal may
        # have cloned the FRESH (empty) Gitea repo into project_path in
        # the meantime. Clear it (guarded) so clone_template starts from
        # a clean slate — parity with the previous behavior.
        if project_path.exists():
            from .workspace_wipe import force_rmtree

            try:
                force_rmtree(project_path)
            except WorkspaceWipeError as exc:
                raise WorkspaceResetError(
                    f"Could not clear pre-clone path {project_path}: {exc}"
                ) from exc

        if clone_fn is None:
            try:
                from scitex.template import clone_template as clone_fn
            except Exception as exc:
                raise WorkspaceResetError(
                    f"scitex.template unavailable for reset of {project_slug}: {exc}"
                ) from exc

        try:
            success = clone_fn(
                VISITOR_TEMPLATE_ID,
                str(project_path),
                git_strategy=None,
            )
        except Exception as exc:
            raise WorkspaceResetError(
                f"Template clone error during reset of {project_slug}: {exc}"
            ) from exc

        if not success:
            raise WorkspaceResetError(
                f"Template clone returned falsy for {project_slug}"
            )

        # VERIFY: template marker must exist after the clone.
        if not verify_template_marker(project_path):
            raise WorkspaceResetError(
                f"Template marker missing after clone: "
                f"{project_path}/{TEMPLATE_MARKER_RELPATH}"
            )

        from .pool_initialization import PoolInitializer

        PoolInitializer._cleanup_project_dev_artifacts(project_path)

        project.git_clone_path = str(project_path)
        project.directory_created = True
        project.save(update_fields=["git_clone_path", "directory_created"])

        logger.info(f"[VisitorPool] Reset visitor workspace: {project_slug}")
        cls.ensure_manuscript_record(project, Path(project_path))
