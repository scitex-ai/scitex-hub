#!/usr/bin/env python3
"""Where an AUTHORIZED project's files live, and whether THIS request may write.

Contract (decided with the Stats side, scitex-stats PR 113 head
``ed3bdf75fb95f5d5b4a733ace069d1f8137a11c2``): a project-scope app reads the dotted
path in ``SCITEX_PROJECT_STORAGE``, imports it, INSTANTIATES the class with no
arguments, and then calls ``project_path(project_id, request)`` and
``can_write(project_id, request)``. Without a usable capability the app fails
CLOSED (``NoHostStorage``) rather than falling back to local folders — so a
half-implemented class here is worse than none at all.

The hub's two hard rules, and the reason this is not a one-line wrapper around the
picker's listing:

* authorization comes from ``find_accessible_project(request.user, project_id)`` —
  the same access-scoped lookup the picker lists from — so an id the caller cannot
  reach has NO path, rather than the caller's own directory;
* the path is the OWNER's canonical root, never the collaborator's. A collaborator
  handed their own base path would silently open a same-named directory that belongs
  to them, which is exactly the failure the protocol's docstring warns about.

Two layers of tests: the logic below runs with NO database (the two collaborators are
stubbed), and the access matrix runs as a TestCase for CI. The stubbed layer exists
because the database-gated layer cannot run in this sandbox, and a contract that is
only checked in CI is a contract that disagrees with its implementation there first.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any, Optional, Protocol, runtime_checkable

from django.contrib.auth.models import User
from django.test import RequestFactory, TestCase
from django.utils.module_loading import import_string

from apps.infra.project_app.models import Project, ProjectMembership
from apps.infra.project_app.services import project_scope
from apps.infra.project_app.services.project_scope import (
    HubProjectProvider,
    HubProjectStorage,
)

PASSWORD = "TestPass123!"  # pragma: allowlist secret
STORAGE_SETTING = "SCITEX_PROJECT_STORAGE"


@runtime_checkable
class _StorageShape(Protocol):
    """The capability shape the Stats side duck-types (its ``ProjectStorage``).

    Mirrored here rather than imported: scitex-stats is not a dependency of the hub,
    and the point of the assertion is that the SHAPE matches, not that a shared class
    was imported.
    """

    def project_path(self, project_id: str, request: Any) -> Optional[str]:
        ...

    def can_write(self, project_id: str, request: Any) -> bool:
        ...


def _request(user=None, path="/apps/stats/"):
    request = RequestFactory().get(path)
    request.user = user if user is not None else SimpleNamespace(is_authenticated=False)
    return request


def _project(owner, slug="alpha", pk=1):
    return SimpleNamespace(owner=owner, slug=slug, pk=pk, name=slug)


def _user(username="someone", pk=9):
    """An authenticated caller.

    Every authorization test must use this: with an unauthenticated request the
    capability returns early, so the assertion would hold for the wrong reason and
    the test would never exercise the rule it names.
    """
    return SimpleNamespace(username=username, is_authenticated=True, pk=pk)


# ---------------------------------------------------------------------------
# the capability the host registers (no database)
# ---------------------------------------------------------------------------


def test_an_unauthorized_or_missing_project_has_no_path(monkeypatch):
    """The picker's own lookup decides: an id it does not resolve has no path."""
    monkeypatch.setattr(project_scope, "find_accessible_project", lambda user, key: None)
    called = []
    monkeypatch.setattr(
        project_scope, "get_project_root_path", lambda u, p: called.append((u, p))
    )

    assert HubProjectStorage().project_path("someone/secret", _request(_user())) is None
    assert called == [], "an unauthorized project must not even be mapped to a path"


def test_the_path_is_the_owners_root_never_the_collaborators(monkeypatch):
    """The caller is a collaborator; the root must be the OWNER's."""
    collaborator = SimpleNamespace(username="collab", is_authenticated=True, pk=2)
    owner = SimpleNamespace(username="owner", is_authenticated=True, pk=1)
    project = _project(owner)
    monkeypatch.setattr(project_scope, "find_accessible_project", lambda user, key: project)

    seen = {}

    def _root(user, proj):
        seen["user"] = user
        return Path("/data/users/owner/proj/alpha")

    monkeypatch.setattr(project_scope, "get_project_root_path", _root)

    path = HubProjectStorage().project_path("owner/alpha", _request(collaborator))

    assert path == "/data/users/owner/proj/alpha"
    assert seen["user"] is owner, "the root must be computed for the OWNER"
    assert "collab" not in path


def test_no_directory_is_created(monkeypatch):
    """Resolving a path must never mkdir — a read-only request cannot write anyway."""
    user = SimpleNamespace(username="collab", is_authenticated=True, pk=2)
    project = _project(SimpleNamespace(username="owner", is_authenticated=True, pk=1))
    monkeypatch.setattr(project_scope, "find_accessible_project", lambda user, key: project)
    monkeypatch.setattr(
        project_scope,
        "get_project_root_path",
        lambda u, p: Path("/data/users/owner/proj/alpha"),
    )

    def _explode(*args, **kwargs):
        raise AssertionError("project_path must not create directories")

    monkeypatch.setattr(Path, "mkdir", _explode)
    monkeypatch.setattr(Path, "touch", _explode)

    assert HubProjectStorage().project_path("owner/alpha", _request(user)) is not None


def test_a_workspace_that_does_not_exist_yields_no_path(monkeypatch):
    """The canonical helper returns None for a root that is absent; pass it through."""
    project = _project(SimpleNamespace(username="owner", is_authenticated=True, pk=1))
    monkeypatch.setattr(project_scope, "find_accessible_project", lambda user, key: project)
    monkeypatch.setattr(project_scope, "get_project_root_path", lambda u, p: None)

    assert HubProjectStorage().project_path("owner/gone", _request(_user())) is None


def test_an_anonymous_request_has_no_path_and_no_write(monkeypatch):
    """No identity, no project: the lookup is never even attempted."""
    called = []
    monkeypatch.setattr(
        project_scope, "find_accessible_project", lambda user, key: called.append(key)
    )
    storage = HubProjectStorage()
    request = _request()  # unauthenticated

    assert storage.project_path("owner/alpha", request) is None
    assert storage.can_write("owner/alpha", request) is False
    assert called == []


def test_can_write_delegates_to_the_models_own_rule(monkeypatch):
    """Write is the project's decision (can_edit), not a second policy here."""
    user = SimpleNamespace(username="collab", is_authenticated=True, pk=2)
    seen = {}

    class _Project:
        owner = SimpleNamespace(username="owner")

        def can_edit(self, candidate):
            seen["user"] = candidate
            return True

    monkeypatch.setattr(project_scope, "find_accessible_project", lambda u, k: _Project())

    assert HubProjectStorage().can_write("owner/alpha", _request(user)) is True
    assert seen["user"] is user


def test_can_write_is_false_for_a_read_only_collaborator(monkeypatch):
    """Read access is not write access — the protocol says so explicitly."""

    class _Project:
        owner = SimpleNamespace(username="owner")

        def can_edit(self, candidate):
            return False

    monkeypatch.setattr(project_scope, "find_accessible_project", lambda u, k: _Project())

    assert HubProjectStorage().can_write("owner/alpha", _request(_user())) is False


def test_can_write_is_false_for_an_unauthorized_project(monkeypatch):
    monkeypatch.setattr(project_scope, "find_accessible_project", lambda u, k: None)
    called = []

    assert HubProjectStorage().can_write("other/secret", _request(_user())) is False
    assert called == []


def test_the_real_path_helper_resolves_under_the_owners_base(settings, tmp_path, monkeypatch):
    """No-DB proof of the owner rule against the REAL ``get_project_root_path``.

    The stubbed tests above prove the capability passes ``project.owner``; this one
    proves what that actually yields: with a real helper and a real BASE_DIR, a
    collaborator's request resolves under the OWNER's directory. It is the half of the
    contract that a stub cannot vouch for, and the access matrix that covers the rest
    only runs where a database exists.
    """
    settings.BASE_DIR = tmp_path
    owner = SimpleNamespace(username="st-owner")
    project = SimpleNamespace(owner=owner, slug="alpha", is_org_owned=False)
    expected = tmp_path / "data" / "users" / "st-owner" / "proj" / "alpha"
    expected.mkdir(parents=True)
    # The decoy: a same-named directory under the CALLER's own base.
    (tmp_path / "data" / "users" / "st-collab" / "proj" / "alpha").mkdir(parents=True)

    monkeypatch.setattr(project_scope, "find_accessible_project", lambda u, k: project)

    path = HubProjectStorage().project_path("st-owner/alpha", _request(_user("st-collab")))

    assert path == str(expected)
    assert "st-collab" not in path


def test_a_request_without_a_user_is_not_an_error(monkeypatch):
    """Fail closed, never raise: the caller is a request handler."""
    storage = HubProjectStorage()
    bare = SimpleNamespace()  # no .user at all

    assert storage.project_path("owner/alpha", bare) is None
    assert storage.can_write("owner/alpha", bare) is False


# ---------------------------------------------------------------------------
# the registration contract (no database)
# ---------------------------------------------------------------------------


def test_the_capability_matches_the_shape_the_stats_side_duck_types():
    assert isinstance(HubProjectStorage(), _StorageShape)


def test_the_class_is_constructible_with_no_arguments():
    """The Stats side imports the dotted path and CALLS it; a factory would break it."""
    registered = import_string("apps.infra.project_app.services.project_scope.HubProjectStorage")

    assert isinstance(registered, type)
    assert isinstance(registered(), _StorageShape)


def test_the_setting_names_the_hub_storage_class():
    from django.conf import settings

    dotted = getattr(settings, STORAGE_SETTING, "")

    assert dotted, f"{STORAGE_SETTING} must be registered for project-scope apps"
    assert import_string(dotted) is HubProjectStorage


def test_the_provider_stays_picker_only():
    """The listing is NOT a path source.

    ``ProjectEntry.detail`` is the owner's username, display metadata. Reading it as a
    filesystem path resolves an unrelated directory that merely shares the project's
    name — so the picker must not grow storage methods and quietly become one.
    """
    provider = HubProjectProvider()

    for name in ("project_path", "can_write"):
        assert not hasattr(provider, name), f"HubProjectProvider must not expose {name}"


# ---------------------------------------------------------------------------
# the access matrix: two users, two projects, real directories (CI)
# ---------------------------------------------------------------------------


class ProjectStorageAccessTest(TestCase):
    """Who gets which path, with the collaborator's own base path as a decoy.

    Every project's canonical root lives under ``settings.BASE_DIR``, so the tests
    point BASE_DIR at a temporary directory and create the real folders there. The
    decoy matters: without a directory that shares the project's name under the
    COLLABORATOR's own base, "they got the owner's path" and "they got their own"
    are indistinguishable in a passing assertion.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        import tempfile

        cls._tmp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls._tmp.cleanup)
        cls.base = Path(cls._tmp.name)

        cls.owner = User.objects.create_user(username="st-owner", password=PASSWORD)
        cls.reader = User.objects.create_user(username="st-reader", password=PASSWORD)
        cls.writer = User.objects.create_user(username="st-writer", password=PASSWORD)
        cls.unrelated = User.objects.create_user(username="st-unrelated", password=PASSWORD)

        cls.alpha = Project.objects.create(
            slug="alpha", owner=cls.owner, name="alpha", visibility="private"
        )
        cls.beta = Project.objects.create(
            slug="beta", owner=cls.owner, name="beta", visibility="private"
        )
        cls.readonly_project = Project.objects.create(
            slug="shared-read", owner=cls.owner, name="shared-read", visibility="private"
        )
        cls.write_project = Project.objects.create(
            slug="shared-write", owner=cls.owner, name="shared-write", visibility="private"
        )
        cls.public_project = Project.objects.create(
            slug="open", owner=cls.owner, name="open", visibility="public"
        )

        ProjectMembership.objects.create(
            project=cls.readonly_project, user=cls.reader, permission_level="read"
        )
        ProjectMembership.objects.create(
            project=cls.write_project, user=cls.writer, permission_level="write"
        )

    def setUp(self):
        self.settings(BASE_DIR=self.base)

    # -- helpers ---------------------------------------------------------

    def _dir(self, username, slug):
        return self.base / "data" / "users" / username / "proj" / slug

    def _make(self, username, slug):
        path = self._dir(username, slug)
        path.mkdir(parents=True, exist_ok=True)
        return path

    def _request(self, user, query=""):
        request = RequestFactory().get("/apps/stats/" + query)
        request.user = User.objects.get(pk=user.pk)
        return request

    def _storage(self):
        return HubProjectStorage()

    # -- the owner -------------------------------------------------------

    def test_the_owner_resolves_their_own_project(self):
        expected = self._make("st-owner", "alpha")

        path = self._storage().project_path("st-owner/alpha", self._request(self.owner))

        assert path == str(expected)
        assert self._storage().can_write("st-owner/alpha", self._request(self.owner)) is True

    def test_a_bare_slug_means_the_callers_own_project(self):
        expected = self._make("st-owner", "beta")

        path = self._storage().project_path("beta", self._request(self.owner))

        assert path == str(expected)

    # -- collaborators ---------------------------------------------------

    def test_a_read_only_collaborator_gets_the_owners_path_and_no_write(self):
        owner_path = self._make("st-owner", "shared-read")
        # The decoy: a same-named directory under the collaborator's OWN base.
        decoy = self._make("st-reader", "shared-read")
        assert decoy.exists()

        storage = self._storage()
        request = self._request(self.reader)

        path = storage.project_path("st-owner/shared-read", request)

        assert path == str(owner_path)
        assert path != str(decoy), "a collaborator must never map to their own base path"
        assert "st-reader" not in path
        assert storage.can_write("st-owner/shared-read", request) is False

    def test_a_write_collaborator_gets_the_owners_path_and_may_write(self):
        owner_path = self._make("st-owner", "shared-write")
        decoy = self._make("st-writer", "shared-write")

        storage = self._storage()
        request = self._request(self.writer)

        path = storage.project_path("st-owner/shared-write", request)

        assert path == str(owner_path)
        assert path != str(decoy)
        assert storage.can_write("st-owner/shared-write", request) is True

    def test_an_admin_collaborator_may_write(self):
        admin = User.objects.create_user(username="st-admin", password=PASSWORD)
        ProjectMembership.objects.create(
            project=self.write_project, user=admin, permission_level="admin"
        )

        assert (
            self._storage().can_write("st-owner/shared-write", self._request(admin)) is True
        )

    # -- everyone else ---------------------------------------------------

    def test_an_unrelated_user_gets_nothing_even_for_a_public_project(self):
        self._make("st-owner", "open")
        storage = self._storage()
        request = self._request(self.unrelated)

        assert storage.project_path("st-owner/open", request) is None
        assert storage.can_write("st-owner/open", request) is False

    def test_an_unrelated_user_cannot_reach_a_project_by_bare_slug(self):
        """A bare slug resolves only against the CALLER's own projects."""
        self._make("st-owner", "alpha")

        assert self._storage().project_path("alpha", self._request(self.unrelated)) is None

    def test_an_unrelated_user_gets_their_own_project_under_a_shared_slug(self):
        """The flip side: their own project of the same slug IS theirs."""
        self._make("st-owner", "alpha")
        own = self._make("st-unrelated", "alpha")

        path = self._storage().project_path("st-unrelated/alpha", self._request(self.unrelated))

        assert path == str(own)

    def test_a_missing_workspace_resolves_to_no_path_and_is_not_created(self):
        """A project row without a directory is not a workspace, and never becomes one."""
        absent = self._dir("st-owner", "beta")
        assert not absent.exists()

        storage = self._storage()
        path = storage.project_path("st-owner/beta", self._request(self.owner))

        assert path is None
        assert not absent.exists(), "resolving a path must not create the directory"

    def test_a_missing_project_id_is_refused(self):
        storage = self._storage()

        assert storage.project_path("", self._request(self.owner)) is None
        assert storage.project_path(None, self._request(self.owner)) is None
