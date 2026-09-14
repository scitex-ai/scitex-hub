#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Slides decks: Marp-style Markdown files under ``<project>/slides/``."""

from __future__ import annotations

import os
import re
from pathlib import Path

from apps.infra.project_app.models import Project

DECKS_DIR = "slides"
FIGURE_EXTENSIONS = (".png", ".svg", ".jpg", ".jpeg", ".gif", ".webp")
_SKIP_DIRS = {".git", "node_modules", ".venv", "venv", "__pycache__", ".cache"}
_MAX_FIGURES = 200
_MAX_REFERENCES = 12


class DeckError(ValueError):
    """A deck request that cannot be honoured (bad name, missing file)."""


def resolve_project(request, ref: str | None = None) -> Project | None:
    """``owner/slug`` (or a bare slug of the user's own), else the current project."""
    requested = ref if ref is not None else request.GET.get("project", "")
    requested = str(requested or "").strip().strip("/")
    if requested:
        owner, _, slug = requested.rpartition("/")
        owner = owner or getattr(request.user, "username", "")
        return (
            Project.objects.select_related("owner")
            .filter(owner__username=owner, slug=slug)
            .first()
        )
    if not request.user.is_authenticated:
        return None
    from apps.infra.project_app.services.project_utils import get_current_project

    return get_current_project(request)


def project_root(project: Project) -> Path:
    return Path(project.get_local_path()).resolve()


def deck_slug(name: str) -> str:
    """A safe file stem: never a path, never empty."""
    stem = Path(str(name or "")).name
    stem = re.sub(r"\.md$", "", stem, flags=re.IGNORECASE)
    stem = re.sub(r"[^A-Za-z0-9._-]+", "-", stem).strip(".-")
    if not stem:
        raise DeckError("deck name is empty")
    return stem[:80]


def deck_path(project: Project, name: str) -> Path:
    root = project_root(project)
    path = (root / DECKS_DIR / f"{deck_slug(name)}.md").resolve()
    if root not in path.parents:
        raise DeckError("deck path escapes the project")
    return path


def list_decks(project: Project) -> list[str]:
    folder = project_root(project) / DECKS_DIR
    if not folder.is_dir():
        return []
    return sorted(p.stem for p in folder.glob("*.md") if p.is_file())


def read_deck(project: Project, name: str) -> str:
    path = deck_path(project, name)
    if not path.is_file():
        raise DeckError("deck not found")
    return path.read_text(encoding="utf-8")


def write_deck(project: Project, name: str, content: str) -> Path:
    path = deck_path(project, name)
    if not project_root(project).is_dir():
        raise DeckError("project has no files yet")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def list_figures(project: Project) -> list[str]:
    """Project-relative image paths (FigRecipe png/svg outputs among them)."""
    root = project_root(project)
    found: list[str] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(
            d for d in dirnames if d not in _SKIP_DIRS and not d.startswith(".")
        )
        for filename in sorted(filenames):
            if filename.lower().endswith(FIGURE_EXTENSIONS):
                found.append(str((Path(dirpath) / filename).relative_to(root)))
                if len(found) >= _MAX_FIGURES:
                    return found
    return found


def resolve_project_file(project: Project, rel_path: str) -> Path:
    root = project_root(project)
    path = (root / str(rel_path or "")).resolve()
    if root not in path.parents or not path.is_file():
        raise DeckError("file not found")
    return path


def _find_references_bib(root: Path) -> Path | None:
    direct = root / "references.bib"
    if direct.is_file():
        return direct
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [
            d for d in dirnames if d not in _SKIP_DIRS and not d.startswith(".")
        ]
        if "references.bib" in filenames:
            return Path(dirpath) / "references.bib"
    return None


def _bib_titles(bib: Path) -> list[str]:
    text = bib.read_text(encoding="utf-8", errors="replace")
    titles = re.findall(r"\btitle\s*=\s*[{\"]+(.+?)[}\"]+\s*,?\s*$", text, re.I | re.M)
    return [re.sub(r"[{}]", "", t).strip() for t in titles][:_MAX_REFERENCES]


def starter_deck(project: Project) -> str:
    """Title slide, one slide per figure, and a references slide when a .bib exists."""
    root = project_root(project)
    title = project.name or project.slug
    slides = [f"# {title}\n\n{project.owner.get_full_name() or project.owner.username}"]
    for figure in list_figures(project):
        caption = Path(figure).stem.replace("_", " ").replace("-", " ")
        slides.append(f"## {caption}\n\n![{caption}](../{figure})")
    bib = _find_references_bib(root)
    if bib is not None:
        items = "\n".join(f"- {t}" for t in _bib_titles(bib)) or "- (see references.bib)"
        slides.append(f"## References\n\n{items}")
    return "---\nmarp: true\n---\n\n" + "\n\n---\n\n".join(slides) + "\n"


# EOF
