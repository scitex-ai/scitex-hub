"""Who may read a file stored under ``MEDIA_ROOT``.

``MEDIA_ROOT`` holds both genuinely public assets (avatars, demo videos) and
private user data (notebooks, workspaces, reports, personal library PDFs,
uploaded BibTeX, compiled manuscripts, arXiv sources, dataset files) at
predictable paths. Media is therefore served by an authorising view
(:mod:`apps.infra.platform_app.views.media`), and this module is the single
policy it consults.

The policy is keyed on the first path component. Anything not listed is
refused, so a new kind of upload is private until someone decides otherwise.
"""

from __future__ import annotations

import posixpath
from typing import Callable, Optional
from urllib.parse import unquote

from django.apps import apps as django_apps

#: Served to anyone. nginx also serves these prefixes directly.
PUBLIC_PREFIXES = frozenset({"avatars", "organization_avatars", "videos"})

#: ``<prefix>/<user id>/...`` — readable by that user only.
USER_ID_PREFIXES = frozenset(
    {"notebooks", "workflows", "environments", "visualizations", "reports", "users"}
)


def normalise_media_path(raw: str) -> Optional[str]:
    """Canonical relative media path, or ``None`` when it is not one."""
    value = str(raw or "")
    for _ in range(3):
        decoded = unquote(value)
        if decoded == value:
            break
        value = decoded
    if not value or "\x00" in value or "\\" in value or value.startswith("/"):
        return None
    parts = value.split("/")
    if any(part in ("", ".", "..") for part in parts):
        return None
    normalised = posixpath.normpath(value)
    if normalised.startswith("..") or normalised in ("", "."):
        return None
    return normalised


def _authenticated(user) -> bool:
    return bool(getattr(user, "is_authenticated", False))


def _model(label: str, name: str):
    try:
        return django_apps.get_model(label, name)
    except LookupError:  # app not installed in this deployment
        return None


def _project_member(user, project) -> bool:
    if project is None or not _authenticated(user):
        return False
    if project.owner_id == user.pk:
        return True
    return project.collaborators.filter(pk=user.pk).exists()


def _manuscript_reader(user, manuscript) -> bool:
    if manuscript is None or not _authenticated(user):
        return False
    if getattr(manuscript, "owner_id", None) == user.pk:
        return True
    collaborators = getattr(manuscript, "collaborators", None)
    if collaborators is not None and collaborators.filter(pk=user.pk).exists():
        return True
    return _project_member(user, getattr(manuscript, "project", None))


def _field_rows(label: str, model: str, fields: tuple[str, ...], name: str):
    cls = _model(label, model)
    if cls is None:
        return []
    from django.db.models import Q

    query = Q()
    for field in fields:
        query |= Q(**{field: name})
    return list(cls.objects.filter(query)[:5])


def _user_library(user, request, name):
    rows = _field_rows(
        "scholar_app", "UserLibrary", ("personal_pdf", "personal_bibtex"), name
    )
    return any(_authenticated(user) and row.user_id == user.pk for row in rows)


def _bibtex_job(user, request, name):
    rows = _field_rows(
        "scholar_app", "BibTeXEnrichmentJob", ("input_file", "output_file"), name
    )
    session_key = getattr(getattr(request, "session", None), "session_key", None)
    for row in rows:
        if _authenticated(user) and row.user_id == user.pk:
            return True
        if row.user_id is None and session_key and row.session_key == session_key:
            return True
    return False


def _dataset_file(user, request, name):
    for row in _field_rows("scholar_app", "DatasetFile", ("local_file",), name):
        dataset = row.dataset
        if getattr(dataset, "visibility", "private") == "public":
            return True
        if not _authenticated(user):
            continue
        if dataset.owner_id == user.pk:
            return True
        if dataset.collaborators.filter(pk=user.pk).exists():
            return True
        if _project_member(user, getattr(dataset, "project", None)):
            return True
    return False


def _manuscript_file(label: str, model: str, fields: tuple[str, ...], extra_owner=None):
    def check(user, request, name):
        for row in _field_rows(label, model, fields, name):
            if extra_owner and _authenticated(user):
                if getattr(row, extra_owner, None) == user.pk:
                    return True
            if _manuscript_reader(user, row.manuscript):
                return True
        return False

    return check


def _any_of(*checks):
    def check(user, request, name):
        return any(c(user, request, name) for c in checks)

    return check


def _search_index(user, request, name):
    # Shared paper index: not tied to one user, but not for anonymous reuse.
    return _authenticated(user) and bool(
        _field_rows("scholar_app", "SearchIndex", ("pdf_file", "bibtex_file"), name)
    )


def _project_scoped(user, request, name):
    # projects/<project id>/...
    parts = name.split("/")
    if len(parts) < 3 or not parts[1].isdigit():
        return False
    project_cls = _model("project_app", "Project")
    if project_cls is None:
        return False
    project = project_cls.objects.filter(pk=int(parts[1])).first()
    return _project_member(user, project)


#: ``first component -> check(user, request, relative_path)``
FIELD_BACKED: dict[str, Callable] = {
    "user_library": _user_library,
    "bibtex_uploads": _bibtex_job,
    "bibtex_enriched": _bibtex_job,
    "dataset_files": _dataset_file,
    "compilations": _manuscript_file(
        "writer_app", "CompilationJob", ("output_pdf",), extra_owner="initiated_by_id"
    ),
    "manuscript_versions": _manuscript_file(
        "writer_app",
        "ManuscriptVersion",
        ("version_file",),
        extra_owner="created_by_id",
    ),
    "manuscript_diffs": _manuscript_file(
        "writer_app", "ManuscriptVersion", ("diff_file",), extra_owner="created_by_id"
    ),
    "manuscripts": _any_of(
        _manuscript_file("writer_app", "Figure", ("file",)),
        _manuscript_file("writer_app", "Table", ("data_file",)),
    ),
    "arxiv_submissions": _manuscript_file(
        "writer_app",
        "ArxivSubmission",
        ("latex_source", "pdf_file"),
        extra_owner="user_id",
    ),
    "scholar": _search_index,
    "projects": _project_scoped,
}


def is_public_media(path: str) -> bool:
    return path.split("/", 1)[0] in PUBLIC_PREFIXES


def may_read_media(user, request, path: str) -> bool:
    """True when ``user`` may read media file ``path`` (already normalised)."""
    head, _, rest = path.partition("/")
    if head in PUBLIC_PREFIXES:
        return True
    if head in USER_ID_PREFIXES:
        owner_id = rest.split("/", 1)[0]
        return _authenticated(user) and owner_id.isdigit() and int(owner_id) == user.pk
    check = FIELD_BACKED.get(head)
    if check is None:
        return False
    return bool(check(user, request, path))
