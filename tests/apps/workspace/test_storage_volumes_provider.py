"""The Storage leaf's volumes provider hands out only the requester's own dirs.

The provider lives at
``apps.workspace.apps_app.services.plugin_volumes.user_volumes`` — generic
hub infrastructure (user -> workspace mapping) consumed via
``SCITEX_STORAGE_VOLUMES_PROVIDER`` by any leaf that measures storage. It
names no plugin.

Real request objects; stub users; the compute-identity lookup stubbed with
``unittest.mock``; no ORM (this dev container's database role cannot create
test databases).
"""

from types import SimpleNamespace
from unittest import mock

from django.contrib.auth.models import AnonymousUser
from django.test import RequestFactory

from apps.workspace.apps_app.services.plugin_volumes import user_volumes


def _request(user, path="/apps/storage/"):
    request = RequestFactory().get(path)
    request.user = user
    return request


def _no_compute_identity():
    from apps.workspace.console_app.models import ComputeIdentity

    manager = mock.Mock()
    manager.filter.return_value.first.return_value = None
    return mock.patch.object(ComputeIdentity, "objects", manager)


class StorageVolumesProviderTests:
    def test_anonymous_gets_no_volumes(self):
        # Arrange
        request = _request(AnonymousUser())
        # Act
        volumes = user_volumes(request)
        # Assert
        assert volumes == []

    def test_workspace_volume_is_the_users_own_data_root(self):
        # Arrange
        user = SimpleNamespace(username="vol_alice", is_authenticated=True)
        request = _request(user)
        # Act
        with _no_compute_identity():
            volumes = user_volumes(request)
        # Assert
        assert [v["key"] for v in volumes] == ["workspace"]
        assert volumes[0]["path"].endswith("/data/users/vol_alice")

    def test_no_compute_home_without_a_compute_identity(self):
        # Arrange
        user = SimpleNamespace(username="vol_bob", is_authenticated=True)
        request = _request(user)
        # Act
        with _no_compute_identity():
            volumes = user_volumes(request)
        # Assert
        assert "compute-home" not in [v["key"] for v in volumes]

    def test_compute_home_appears_with_a_compute_identity(self):
        # Arrange
        from apps.workspace.console_app.models import ComputeIdentity

        user = SimpleNamespace(username="vol_cara", is_authenticated=True)
        request = _request(user)
        identity = SimpleNamespace(username="cara-compute")
        manager = mock.Mock()
        manager.filter.return_value.first.return_value = identity
        # Act
        with mock.patch.object(ComputeIdentity, "objects", manager):
            volumes = user_volumes(request)
        # Assert
        by_key = {v["key"]: v for v in volumes}
        assert set(by_key) == {"workspace", "compute-home"}
        assert by_key["compute-home"]["path"].endswith("cara-compute")
