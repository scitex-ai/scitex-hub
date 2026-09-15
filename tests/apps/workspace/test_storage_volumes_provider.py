"""The Storage leaf's volumes provider hands out only the requester's own dirs.

Real ORM, real request objects; no mocks.
"""

from django.contrib.auth.models import AnonymousUser, User
from django.test import RequestFactory, TestCase

from apps.workspace.storage_app.volumes import user_volumes


class StorageVolumesProviderTests(TestCase):
    def test_anonymous_gets_no_volumes(self):
        # Arrange
        request = RequestFactory().get("/apps/storage/")
        request.user = AnonymousUser()
        # Act
        volumes = user_volumes(request)
        # Assert
        assert volumes == []

    def test_workspace_volume_is_the_users_own_data_root(self):
        # Arrange
        user = User.objects.create_user("vol_alice", password="x")
        request = RequestFactory().get("/apps/storage/")
        request.user = user
        # Act
        paths = [v["path"] for v in user_volumes(request)]
        # Assert
        assert paths[0].endswith("/data/users/vol_alice")

    def test_no_compute_home_without_a_compute_identity(self):
        # Arrange
        user = User.objects.create_user("vol_bob", password="x")
        request = RequestFactory().get("/apps/storage/")
        request.user = user
        # Act
        keys = [v["key"] for v in user_volumes(request)]
        # Assert
        assert "compute-home" not in keys
