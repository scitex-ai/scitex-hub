"""Clew store access follows the Hub's project permission model (scitex-hub#1225).

DEFECT
------
``HubProjectStore.store_access`` refused every caller who was not the
project's individual owner ("Shared project stores require project-level
access control", HTTP 503), so no collaborator could inspect a shared
project's provenance in Clew, while Live Paper showed them the same evidence.

CONTRACT
--------
* read  -- the owner and every project member (any permission level) receive
  the PROJECT's store: the owner's configured tenant and this project's
  explicit Clew scope. Never the caller's own tenant, never a same-named
  project of theirs.
* write -- ``HubProjectStorage.can_write`` (``Project.can_edit``): the owner
  and members with ``write``/``admin`` permission; viewers are read-only.
* non-members and anonymous callers get neither.

Behavioural: real users, projects and memberships in the Django test DB and
the real Hub providers. The PostgreSQL tenant/HTTP path of the same matrix is
covered by ``tests.security.test_clew_tenant_store`` (disposable cluster).
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from django.contrib.auth.models import AnonymousUser, User
from django.test import RequestFactory, override_settings
from scitex_sdk.host import CapabilityUnavailable

from apps.infra.project_app.models import Project, ProjectMembership
from apps.infra.project_app.services.project_scope import HubProjectStorage
from apps.infra.project_app.services.project_store import HubProjectStore

pytestmark = [pytest.mark.security, pytest.mark.django_db]

OWNER_TENANT = str(uuid4())
VIEWER_TENANT = str(uuid4())
PROJECT_SCOPE = "clew-shared-paper"
VIEWER_OWN_SCOPE = "clew-viewer-own-paper"
MEMBERS = {
    # name: (role, permission_level)
    "maintainer": ("admin", "admin"),
    "writer": ("collaborator", "write"),
    "viewer": ("viewer", "read"),
}
READERS = ("owner", "maintainer", "writer", "viewer")
WRITERS = ("owner", "maintainer", "writer")
REFUSED_READERS = ("outsider", "anonymous")
REFUSED_WRITERS = ("viewer", "outsider", "anonymous")


@pytest.fixture
def world():
    users = {
        name: User.objects.create_user(username=f"clew-perm-{name}")
        for name in ("owner", *MEMBERS, "outsider")
    }
    # bulk_create skips repository-provisioning signals (no Gitea, no disk).
    shared, viewer_own = Project.objects.bulk_create(
        [
            Project(owner=users["owner"], name="Shared paper", slug="shared-paper"),
            # Same slug, owned by a member: must never be what they read.
            Project(owner=users["viewer"], name="Own paper", slug="shared-paper"),
        ]
    )
    for name, (role, permission) in MEMBERS.items():
        ProjectMembership.objects.create(
            project=shared, user=users[name], role=role, permission_level=permission
        )
    secrets = {
        str(users["owner"].pk): {
            "tenant_id": OWNER_TENANT,
            "dsn": "postgresql://owner-tenant.invalid/clew",
            "projects": {str(shared.pk): PROJECT_SCOPE},
        },
        str(users["viewer"].pk): {
            "tenant_id": VIEWER_TENANT,
            "dsn": "postgresql://viewer-tenant.invalid/clew",
            "projects": {str(viewer_own.pk): VIEWER_OWN_SCOPE},
        },
    }
    users["anonymous"] = AnonymousUser()
    with override_settings(SCITEX_STORE_TENANT_SECRETS=secrets):
        yield {"users": users, "key": f"{users['owner'].username}/shared-paper"}


def _request(user):
    request = RequestFactory().get("/apps/clew/")
    request.user = user
    return request


@pytest.mark.parametrize("name", READERS)
def test_project_members_read_the_projects_own_tenant(world, name):
    # Arrange
    store = HubProjectStore()
    request = _request(world["users"][name])
    # Act
    access = store.store_access(world["key"], request)
    # Assert
    assert str(access.tenant_id) == OWNER_TENANT


@pytest.mark.parametrize("name", READERS)
def test_project_members_read_only_this_projects_scope(world, name):
    # Arrange
    store = HubProjectStore()
    request = _request(world["users"][name])
    # Act
    access = store.store_access(world["key"], request)
    # Assert
    assert access.project_scope == PROJECT_SCOPE


@pytest.mark.parametrize("name", REFUSED_READERS)
def test_non_members_and_anonymous_cannot_read(world, name):
    # Arrange
    store = HubProjectStore()
    request = _request(world["users"][name])
    # Act
    # Assert
    with pytest.raises(CapabilityUnavailable):
        store.store_access(world["key"], request)


@pytest.mark.parametrize("name", WRITERS)
def test_owner_and_maintainers_may_write(world, name):
    # Arrange
    request = _request(world["users"][name])
    # Act
    allowed = HubProjectStorage().can_write(world["key"], request)
    # Assert
    assert allowed is True


@pytest.mark.parametrize("name", REFUSED_WRITERS)
def test_viewers_non_members_and_anonymous_may_not_write(world, name):
    # Arrange
    request = _request(world["users"][name])
    # Act
    allowed = HubProjectStorage().can_write(world["key"], request)
    # Assert
    assert allowed is False


def test_member_still_reads_their_own_project_with_their_own_tenant(world):
    # Arrange
    viewer = world["users"]["viewer"]
    # Act
    own = HubProjectStore().store_access(
        f"{viewer.username}/shared-paper", _request(viewer)
    )
    # Assert
    assert (str(own.tenant_id), own.project_scope) == (VIEWER_TENANT, VIEWER_OWN_SCOPE)


def test_unmapped_project_says_it_is_not_configured(world):
    # Arrange
    request = _request(world["users"]["viewer"])
    # Act
    # Assert
    with override_settings(SCITEX_STORE_TENANT_SECRETS={}):
        with pytest.raises(CapabilityUnavailable, match="not configured"):
            HubProjectStore().store_access(world["key"], request)
