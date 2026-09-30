#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
User Library Service — thin hub wrapper over the scitex-scholar package.

Every hub user is a unix user, so the library is simply that user's
``~/.scitex/scholar/`` tree (pwd-resolved; ``USER_DATA_ROOT/users/<name>``
fallback when no unix account exists, e.g. fresh signups in containers).

All storage behavior — ``MASTER/<paper_id>/`` writes, metadata schema,
legacy fallbacks — lives in
:mod:`scitex_scholar.storage._master_store`. This module only resolves
*whose* library and *which* project link; it contains no file-format
knowledge. Requires scitex-scholar>=1.13 (``master_*`` verbs).
"""

import logging
import pwd
from pathlib import Path
from typing import Dict, List, Optional

from django.conf import settings
from django.contrib.auth.models import User

logger = logging.getLogger(__name__)

try:  # Package PathManager: the offered seam for the canonical layout.
    from scitex_scholar.config.core._PathManager import PathManager
except ImportError:  # pragma: no cover - old leaf; manual same-layout fallback
    PathManager = None

from scitex_scholar.storage._master_store import (
    add_paper as _leaf_add_paper,
)
from scitex_scholar.storage._master_store import (
    get_paper_path as _leaf_get_paper_path,
)
from scitex_scholar.storage._master_store import (
    list_papers as _leaf_list_papers,
)
from scitex_scholar.storage._master_store import (
    paper_id_for as _paper_id,
)


class UserLibraryService:
    """
    Thin per-user handle: path resolution here, storage in the leaf.

    Public surface (kept stable for views):
    ``library_path``, ``add_paper``, ``get_paper_path``,
    ``ensure_project_link``, ``prune_project_link``, ``link_to_project``,
    ``unlink_from_project``, ``list_user_papers``, ``deduplicate``.
    """

    def __init__(self, user: User):
        """
        Initialize service for a specific user.

        Args:
            user: Django User instance
        """
        self.user = user
        self.scholar_dir = self._get_user_scholar_dir()
        self.library_path = self.scholar_dir / "library"
        self._pm = PathManager(scholar_dir=self.scholar_dir) if PathManager else None
        self._ensure_structure()

    def _get_user_scholar_dir(self) -> Path:
        """
        Get the user's ``~/.scitex/scholar`` dir.

        Every hub user is a unix user: pwd-resolve the home. Fresh signups
        without a unix account yet fall back to the managed
        ``{USER_DATA_ROOT}/users/<name>/.scitex/scholar`` tree, else the
        package default setting.
        """
        try:
            home = Path(pwd.getpwnam(self.user.username).pw_dir)
            return home / ".scitex" / "scholar"
        except KeyError:
            pass
        if settings.USER_DATA_ROOT:
            # USER_DATA_ROOT may already point at the users tree itself
            # (e.g. /app/data/users); never double the "users" segment.
            root = settings.USER_DATA_ROOT
            users_root = root if root.name == "users" else root / "users"
            return (
                users_root
                / self.user.username
                / ".scitex"
                / "scholar"
            )
        return settings.SCITEX_SCHOLAR_USER_LIBRARY_ROOT.parent

    def _get_user_library_path(self) -> Path:
        """Legacy accessor: the library root (kept for callers)."""
        return self._get_user_scholar_dir() / "library"

    def _ensure_structure(self):
        """Create the package-canonical library structure if missing."""
        if self._pm is not None:
            self._pm.get_library_master_dir()
        else:  # old leaf: same layout, created manually
            (self.library_path / "MASTER").mkdir(parents=True, exist_ok=True)
        logger.info(
            f"Ensured package-layout library for user {self.user.username} "
            f"at {self.library_path}"
        )

    def add_paper(
        self,
        identifier: str,
        id_type: str,
        pdf_path: Optional[Path] = None,
        bibtex_content: Optional[str] = None,
        metadata: Optional[Dict] = None,
    ) -> Dict[str, Path]:
        """Add paper to user library (leaf ``master_add_paper``)."""
        return _leaf_add_paper(
            self.library_path,
            identifier,
            id_type,
            pdf_path=pdf_path,
            bibtex_content=bibtex_content,
            metadata=metadata,
        )

    def get_paper_path(
        self, identifier: str, id_type: str, file_type: str = "pdf"
    ) -> Optional[Path]:
        """Absolute path to paper file in user library (leaf lookup)."""
        return _leaf_get_paper_path(
            self.library_path, identifier, id_type, file_type
        )

    def ensure_project_link(self, project_path: Path) -> Optional[Path]:
        """
        Link ``<project>/.scitex/scholar/library`` to this user's home
        library using the package verb (``link_project_tree``).

        Idempotent. Returns the link path, or None when the package is
        not importable. On leaves predating ``library_root`` (improved in
        scitex-scholar#182) the identical symlink is created manually.
        """
        project_path = Path(project_path)
        # Contract from #1029: a scaffold placeholder with no content is safe
        # to adopt. The leaf's link_project_tree (1.13.0) refuses ANY existing
        # path without --force, so clear an empty dir BEFORE delegating —
        # otherwise the refactor to leaf verbs (#1030) regresses the adoption
        # the hub already promised. Non-empty dirs still refuse via the leaf.
        _link = project_path / ".scitex" / "scholar" / "library"
        try:
            if _link.is_dir() and not _link.is_symlink() and not any(_link.iterdir()):
                _link.rmdir()
        except OSError:
            pass
        try:
            from scitex_scholar.cli._project_tree import link_project_tree

            try:
                return link_project_tree(
                    project_path, library_root=self.library_path
                )
            except FileExistsError:
                # Raced or missed the pre-check above: adopt an empty
                # placeholder now, then retry once. Anything with content
                # still refuses.
                try:
                    if _link.is_dir() and not _link.is_symlink() and not any(
                        _link.iterdir()
                    ):
                        _link.rmdir()
                        return link_project_tree(
                            project_path, library_root=self.library_path
                        )
                except OSError:
                    pass
                raise
            except TypeError:  # leaf predates library_root: same link, manual
                target = self.library_path.resolve()
                link_parent = project_path / ".scitex" / "scholar"
                link_parent.mkdir(parents=True, exist_ok=True)
                link = link_parent / "library"
                if link.is_symlink() and link.readlink() == target:
                    return link
                if link.is_symlink():
                    raise FileExistsError(
                        f"{link} is a symlink elsewhere; refusing to "
                        "replace without force"
                    )
                if link.is_dir() and not any(link.iterdir()):
                    # Scaffold placeholder with no content: safe to adopt.
                    link.rmdir()
                elif link.exists():
                    raise FileExistsError(
                        f"{link} occupied; refusing to replace without force"
                    )
                link.symlink_to(self.library_path)
                return link
        except ImportError:
            logger.warning("scitex_scholar unavailable; project link skipped")
            return None

    def prune_project_link(self, project_path: Path) -> bool:
        """
        Remove the ``.scitex/scholar/library`` symlink when it points at
        this user's library. Returns True when removed.
        """
        link = Path(project_path) / ".scitex" / "scholar" / "library"
        if link.is_symlink():
            try:
                if link.readlink() == self.library_path.resolve():
                    link.unlink()
                    return True
            except OSError:
                pass
        return False

    def link_to_project(self, paper_rel_path: str, project_path: Path):
        """
        Create project access to the user library.

        Legacy signature (per-paper) kept for callers: the package links
        the whole library tree, so this ensures the project link exists.
        The per-paper symlink farm (``library/papers/``) is retired.

        Args:
            paper_rel_path: Ignored except for logging (kept for signature).
            project_path: Absolute path to project directory
        """
        link = self.ensure_project_link(Path(project_path))
        if link is None:
            logger.warning(f"Source file not found: {paper_rel_path}")
            return
        logger.info(f"Linked {link} for project {Path(project_path).name}")

    def unlink_from_project(self, paper_filename: str, project_path: Path):
        """
        Remove project access to a paper.

        The package links the whole library tree, so per-paper removal is a
        no-op for the filesystem; the legacy per-paper symlink (if left over
        from the pre-package layout) is still cleaned up. Callers remove the
        tree link via :meth:`prune_project_link` once no papers remain.

        Args:
            paper_filename: Filename of paper (legacy symlink name)
            project_path: Absolute path to project directory
        """
        legacy_path = (
            Path(project_path)
            / ".scitex"
            / "scholar"
            / "library"
            / "papers"
            / paper_filename
        )
        if legacy_path.is_symlink():
            legacy_path.unlink()
            logger.info(
                f"Unlinked legacy {paper_filename} from project "
                f"{Path(project_path).name}"
            )
        elif legacy_path.exists():
            logger.warning(f"File exists but is not a symlink: {legacy_path}")

    def list_user_papers(self) -> List[Dict]:
        """List all papers in user's library (leaf ``master_list_papers``)."""
        return _leaf_list_papers(self.library_path)

    def deduplicate(self) -> Dict:
        """
        Find and report duplicate papers in user library.

        Returns:
            Dict with deduplication stats: {
                'duplicates_found': int,
                'space_saved_bytes': int,
                'suggestions': List[Dict]
            }

        Note:
            This is a stub for future implementation. Actual deduplication
            logic should be delegated to scitex.scholar package.
        """
        # TODO: Implement duplicate detection using file hashes
        # TODO: Delegate to scitex.scholar.deduplicate() when available
        logger.info(f"Deduplication not yet implemented for user {self.user.username}")
        return {
            "duplicates_found": 0,
            "space_saved_bytes": 0,
            "suggestions": [],
        }


# EOF
