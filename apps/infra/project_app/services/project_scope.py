"""Hub provider for the SciTeX SDK project picker (project-scope apps).

Implements the SDK ``ProjectProvider`` contract (``scitex_ui.project_scope``)
structurally, so the hub does not need that release to import:

- the listing is only projects the user can access: owned plus shared through
  ``ProjectMembership``; other users' projects never appear, public or not;
- the last visited project is ``UserProfile.last_active_repository``;
- an explicit project (``?project=owner/slug``) always wins and becomes the
  last visited one; an inaccessible explicit project resolves to ``None``
  instead of silently opening the stored one.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from django.db.models import Q

from apps.infra.project_app.models import Project
from apps.infra.project_app.services.filesystem.paths import get_project_root_path

PROJECT_QUERY_PARAM = "project"


@dataclass(frozen=True)
class ProjectEntry:
    id: str
    name: str
    detail: str = ""

    def as_option(self) -> dict:
        option = {"id": self.id, "name": self.name}
        if self.detail:
            option["detail"] = self.detail
        return option


def project_key(project: Project) -> str:
    return f"{project.owner.username}/{project.slug}"


def accessible_projects(user):
    if not getattr(user, "is_authenticated", False):
        return Project.objects.none()
    return (
        Project.objects.filter(Q(owner=user) | Q(collaborators=user))
        .select_related("owner")
        .distinct()
        .order_by("-updated_at")
    )


def find_accessible_project(user, key: Optional[str]) -> Optional[Project]:
    """``owner/slug``, or a bare slug meaning the user's own project."""
    if not key:
        return None
    owner, _, slug = key.strip().strip("/").rpartition("/")
    lookup = {"slug": slug, "owner__username": owner or user.username}
    return accessible_projects(user).filter(**lookup).first()


def last_visited_project(user) -> Optional[Project]:
    profile = getattr(user, "profile", None)
    stored = getattr(profile, "last_active_repository", None)
    if stored is None:
        return None
    return accessible_projects(user).filter(pk=stored.pk).first()


def remember_last_visited(user, project: Project) -> None:
    profile = getattr(user, "profile", None)
    if profile is None or profile.last_active_repository_id == project.pk:
        return
    profile.last_active_repository = project
    profile.save(update_fields=["last_active_repository"])


def resolve_scoped_project(request, explicit: Optional[str] = None) -> Optional[Project]:
    """The project a project-scope app opens: explicit URL project, else last visited."""
    user = request.user
    if explicit is None:
        explicit = request.GET.get(PROJECT_QUERY_PARAM)
    if explicit:
        project = find_accessible_project(user, explicit)
        if project is not None:
            remember_last_visited(user, project)
        return project
    return last_visited_project(user)


def project_for_scope_app(request) -> Optional[Project]:
    """``resolve_scoped_project`` plus the hub's older default when nothing is stored."""
    if request.GET.get(PROJECT_QUERY_PARAM):
        return resolve_scoped_project(request)
    from apps.infra.project_app.services.project_utils import get_current_project

    project = resolve_scoped_project(request)
    if project is None:
        project = get_current_project(request)
        # The leaf picker shows the provider's last visited project as current.
        if project is not None and find_accessible_project(request.user, project_key(project)):
            remember_last_visited(request.user, project)
    return project


class HubProjectProvider:
    """The SDK ``ProjectProvider`` over the hub's database."""

    def project_id(self, project: Project) -> str:
        return project_key(project)

    def list_projects(self, request) -> list[ProjectEntry]:
        return [
            ProjectEntry(
                id=project_key(project),
                name=project.name,
                detail=project.owner.username,
            )
            for project in accessible_projects(request.user)
        ]

    def last_visited(self, request) -> Optional[str]:
        project = last_visited_project(request.user)
        return project_key(project) if project else None

    def remember(self, request, project_id: str) -> None:
        project = find_accessible_project(request.user, project_id)
        if project is not None:
            remember_last_visited(request.user, project)


class HubProjectStorage:
    """Where an authorized project's files live, and whether THIS request may write.

    The capability a project-scope app reads from ``SCITEX_PROJECT_STORAGE`` (see
    scitex-stats PR 113): the app imports the dotted path, instantiates the class with
    no arguments, then asks per request. Deliberately separate from
    :class:`HubProjectProvider` — that one is a picker, and its ``ProjectEntry.detail``
    is the owner's username, display metadata that must never be read as a path.

    Two rules, both fail-closed:

    * **authorization first.** The project is resolved through
      ``find_accessible_project(request.user, project_id)`` — the same access-scoped
      lookup the picker lists from — so a project id this request cannot reach has no
      path at all, rather than falling back to a directory that happens to share its
      name.
    * **the owner's root, never the collaborator's.** The path is
      ``get_project_root_path(project.owner, project)``: a collaborator handed their
      own base path would silently open a same-named directory that belongs to them.

    Nothing here creates directories. ``get_project_root_path`` returns ``None`` for a
    project whose root is absent, and that ``None`` is passed through as "this project
    has no workspace yet" instead of being turned into one.
    """

    def project_path(self, project_id: str, request) -> Optional[str]:
        """The project's storage root, or ``None`` when this request has none."""
        project = self._authorized_project(project_id, request)
        if project is None:
            return None
        root = get_project_root_path(project.owner, project)
        return str(root) if root is not None else None

    def can_write(self, project_id: str, request) -> bool:
        """Reading is not writing: the project's own rule decides."""
        project = self._authorized_project(project_id, request)
        if project is None:
            return False
        return bool(project.can_edit(request.user))

    @staticmethod
    def _authorized_project(project_id: Optional[str], request):
        """The project this request may act on, or ``None``.

        Authorization only: a missing identity, or a missing/blank project id, is a
        REFUSAL here rather than an exception — those are caller mistakes a request
        handler must survive, and the answer is the same as "not yours".

        Backend faults are NOT swallowed. A database error while resolving access, or a
        filesystem error while resolving the root, propagates: Django turns it into a
        500, which is the honest outcome for an infrastructure failure. Reporting one as
        "no project" would present a broken host as an unauthorized caller and send
        whoever is debugging it after the wrong bug.
        """
        user = getattr(request, "user", None)
        if user is None or not getattr(user, "is_authenticated", False):
            return None
        if not project_id:
            return None
        return find_accessible_project(user, project_id)
