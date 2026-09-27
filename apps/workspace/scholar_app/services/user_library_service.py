#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
User Library Service — thin hub wrapper over the scitex-scholar package.

Every hub user is a unix user, so the library is simply that user's
``~/.scitex/scholar/`` tree (pwd-resolved; ``USER_DATA_ROOT/users/<name>``
fallback when no unix account exists, e.g. fresh signups in containers).

Layout follows the package's PathManager PATH_STRUCTURE exactly —
``library/MASTER/<paper_id>/`` for paper storage (pdf + bib + metadata.json,
which the package's library index reads), ``library/<project>/`` for
per-project trees. Project roots get ``.scitex/scholar/library`` symlinked
to the home library via the package's ``link_project_tree``.

Storage Strategy:
    - Papers stored once in user library (deduplicated)
    - Projects see the whole library through one symlink (package verb)
    - Django tracks paths via CharField (relative to the library root)
    - No hub-invented directories: `papers/{doi,pmid,arxiv}/`, `collections/`
      and `metadata/` are legacy and no longer created.
"""

import json
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


def _paper_id(identifier: str, id_type: str) -> str:
    """Filesystem-safe MASTER/<paper_id> for an identifier."""
    safe = "".join(
        c if (c.isalnum() or c in ("-", "_", ".")) else "_" for c in identifier
    ).strip("._")[:120]
    if id_type and not safe.lower().startswith(id_type.lower()):
        safe = f"{id_type}-{safe}" if safe else id_type
    return safe or "unknown"


class UserLibraryService:
    """
    Manages user-level scholar library with symlinks.

    This service is a thin wrapper that:
    1. Determines user-specific library paths
    2. Delegates actual paper management to scitex.scholar package
    3. Ensures directory structure exists
    4. Provides simple interface for Django views/models
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
        """
        Add paper to user library under ``MASTER/<paper_id>/``.

        Args:
            identifier: Paper identifier (DOI, PMID, arXiv ID)
            id_type: Type of identifier ('doi', 'pmid', 'arxiv')
            pdf_path: Optional path to PDF file to copy
            bibtex_content: Optional BibTeX content to save
            metadata: Optional package-schema metadata dict; when absent a
                minimal one is derived from identifier/id_type so the
                package library index can read the entry.

        Returns:
            Dict with 'pdf' and 'bibtex' paths (relative to library root)
        """
        paper_id = _paper_id(identifier, id_type)
        paper_dir = self.library_path / "MASTER" / paper_id
        paper_dir.mkdir(parents=True, exist_ok=True)

        result = {}

        # Copy PDF if provided
        if pdf_path and Path(pdf_path).exists():
            dest_pdf = paper_dir / f"{paper_id}.pdf"
            if not dest_pdf.exists():
                import shutil

                shutil.copy2(pdf_path, dest_pdf)
                logger.info(f"Added PDF for {identifier} to user library")
            result["pdf"] = dest_pdf.relative_to(self.library_path)

        # Save BibTeX if provided
        if bibtex_content:
            dest_bib = paper_dir / f"{paper_id}.bib"
            dest_bib.write_text(bibtex_content)
            logger.info(f"Added BibTeX for {identifier} to user library")
            result["bibtex"] = dest_bib.relative_to(self.library_path)

        # metadata.json: the package index's primary source. Merge caller
        # metadata over the derived skeleton, never the reverse.
        skeleton = {
            "metadata": {
                "id": {"doi": None, "arxiv_id": None, "pmid": None},
                "basic": {
                    "title": None,
                    "year": None,
                    "authors": [],
                    "abstract": None,
                },
                "publication": {},
                "access": {},
                "citation": {},
            }
        }
        key_map = {"doi": "doi", "arxiv": "arxiv_id", "pmid": "pmid"}
        if id_type in key_map:
            skeleton["metadata"]["id"][key_map[id_type]] = identifier
        merged = dict(skeleton["metadata"])
        # Fold flat search-result keys into their package sections so no
        # caller can produce an entry whose basic.title is None. Explicit
        # nested sections win over flat keys.
        flat = dict(metadata or {})
        for section, values in flat.items():
            if isinstance(values, dict):
                merged.setdefault(section, {}).update(values)
        # Skeleton placeholders are None (key present) — setdefault would
        # keep them; fill only gaps.
        def _fill(section, key, value):
            if value is None:
                return
            target = merged.setdefault(section, {})
            if target.get(key) is None:
                target[key] = value

        for key in ("title", "year", "authors", "abstract"):
            _fill("basic", key, flat.get(key))
        _fill("publication", "journal", flat.get("journal"))
        for key in ("doi", "arxiv_id", "pmid"):
            _fill("id", key, flat.get(key))
        for section, values in flat.items():
            if not isinstance(values, dict) and section not in (
                "title",
                "year",
                "authors",
                "abstract",
                "journal",
                "doi",
                "arxiv_id",
                "pmid",
            ):
                merged[section] = values
        skeleton["metadata"] = merged
        (paper_dir / "metadata.json").write_text(
            json.dumps(skeleton, indent=2, ensure_ascii=False)
        )

        return result

    def get_paper_path(
        self, identifier: str, id_type: str, file_type: str = "pdf"
    ) -> Optional[Path]:
        """
        Get absolute path to paper file in user library.

        Args:
            identifier: Paper identifier
            id_type: Type of identifier ('doi', 'pmid', 'arxiv')
            file_type: File type ('pdf' or 'bib')

        Returns:
            Absolute path to file, or None if not found
        """
        safe_id = _paper_id(identifier, id_type)
        paper_path = self.library_path / "MASTER" / safe_id / f"{safe_id}.{file_type}"
        if paper_path.exists():
            return paper_path
        # Legacy hub layout (pre-package): papers/<id_type>/<safe>.<ext>
        legacy_safe = identifier.replace("/", "_").replace(":", "_")
        legacy_path = (
            self.library_path / "papers" / id_type / f"{legacy_safe}.{file_type}"
        )
        if legacy_path.exists():
            return legacy_path
        return None

    def ensure_project_link(self, project_path: Path) -> Optional[Path]:
        """
        Link ``<project>/.scitex/scholar/library`` to this user's home
        library using the package verb (``link_project_tree``).

        Idempotent. Returns the link path, or None when the package is
        not importable. On leaves predating ``library_root`` (improved in
        scitex-scholar#182) the identical symlink is created manually.
        """
        project_path = Path(project_path)
        try:
            from scitex_scholar.cli._project_tree import link_project_tree

            try:
                return link_project_tree(
                    project_path, library_root=self.library_path
                )
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
        """
        List all papers in user's library (package ``MASTER/`` store,
        plus legacy ``papers/`` entries not yet migrated).

        Returns:
            List of dicts with paper info: {
                'identifier': str,
                'id_type': str,
                'pdf_path': Path,
                'bib_path': Path
            }
        """
        papers = []
        seen = set()

        master = self.library_path / "MASTER"
        if master.is_dir():
            for pdf_file in sorted(master.glob("*/*.pdf")):
                paper_id = pdf_file.parent.name
                bib_file = pdf_file.with_name(f"{paper_id}.bib")
                papers.append(
                    {
                        "identifier": paper_id,
                        "id_type": "master",
                        "pdf_path": pdf_file,
                        "bib_path": bib_file if bib_file.exists() else None,
                    }
                )
                seen.add(pdf_file.resolve())

        for id_type in ["doi", "pmid", "arxiv"]:
            type_dir = self.library_path / "papers" / id_type
            if not type_dir.exists():
                continue

            for pdf_file in type_dir.glob("*.pdf"):
                if pdf_file.resolve() in seen:
                    continue
                identifier = pdf_file.stem
                bib_file = pdf_file.with_suffix(".bib")

                papers.append(
                    {
                        "identifier": identifier,
                        "id_type": id_type,
                        "pdf_path": pdf_file,
                        "bib_path": bib_file if bib_file.exists() else None,
                    }
                )

        return papers

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
