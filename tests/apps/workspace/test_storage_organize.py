"""Organize tabs for the Storage app: usage donut, duplicates, move planning.

DB-free by design (this dev container's database role cannot create test
databases, so no test here may touch the ORM): users are stub objects and the
upstream volume resolution is stubbed with fake ``Volume``/``VolumeStatus``
rows. scitex-storage API calls that need system binaries (fd/fclones) are
stubbed so the tests are hermetic. The whole module skips when the optional
``scitex_storage`` package is absent (same gating as the mount itself).
"""

import pytest

scitex_storage = pytest.importorskip("scitex_storage")

from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from django.contrib.auth.models import AnonymousUser
from django.test import RequestFactory

from apps.workspace.storage_app import organize
from apps.workspace.storage_app import views as storage_views
from apps.workspace.storage_app.organize import donut_segments


@pytest.fixture(autouse=True)
def _stub_chrome_queries():
    """Neutralize hub-chrome DB queries these DB-free tests never touch.

    * The project context processor resolves ANY two-segment path —
      including /apps/storage/ — against the Project table.
    * The sidebar pins resolver queries ModuleInstallation for the user.
    * The site dock resolver queries AppsModule installations.
    """
    from apps.infra.project_app.models import Project

    manager = mock.Mock()
    manager.select_related.return_value.get.side_effect = Project.DoesNotExist
    with (
        mock.patch.object(Project, "objects", manager),
        mock.patch(
            "apps.workspace.apps_app.views.launcher.get_pinned_module_names",
            return_value=[],
            create=True,
        ),
        mock.patch(
            "apps.infra.public_app.templatetags.site_dock.dock_items",
            return_value=[],
        ),
    ):
        yield


def _user(name="org_test"):
    return SimpleNamespace(username=name, is_authenticated=True)


def _request(user, path="/apps/storage/"):
    request = RequestFactory().get(path)
    request.user = user
    return request


def _fake_volume(key="workspace", label="Workspace files", path="/tmp"):
    from scitex_storage._django import volumes as _volumes

    return _volumes.Volume(key=key, label=label, path=Path(path), machine="test")


def _fake_status(volume, used=60, total=100, status=None):
    from scitex_storage._django import volumes as _volumes

    return _volumes.VolumeStatus(
        volume, status or _volumes.REACHABLE, total, used, total - used
    )


def _patch_volumes(volumes_list, statuses_list):
    from scitex_storage._django import volumes as _volumes

    return (
        mock.patch.object(_volumes, "resolve_user_volumes", return_value=volumes_list),
        mock.patch.object(_volumes, "measure_all", return_value=statuses_list),
    )


class TestDonutSegments:
    def test_fractions_sum_to_one(self):
        # Arrange
        items = [("a", 50), ("b", 30), ("c", 20)]
        # Act
        segments = donut_segments(items)
        # Assert
        assert len(segments) == 3
        assert abs(sum(s.fraction for s in segments) - 1.0) < 1e-9
        assert segments[0].offset == 0.0
        assert segments[1].offset == -(50 / 100) * organize.DONUT_C

    def test_zero_and_negative_values_dropped(self):
        # Act
        segments = donut_segments([("a", 0), ("b", -5), ("c", 10)])
        # Assert
        assert [s.label for s in segments] == ["c"]
        assert segments[0].fraction == 1.0

    def test_empty_input_yields_no_segments(self):
        assert donut_segments([]) == []
        assert donut_segments([("a", 0)]) == []


class TestRunBounded:
    def test_success_returns_value(self):
        ok, value = organize._run_bounded(lambda: 42, 5.0)
        assert (ok, value) == (True, 42)

    def test_exception_is_reported_not_raised(self):
        boom = RuntimeError("boom")

        def _raise():
            raise boom

        ok, err = organize._run_bounded(_raise, 5.0)
        assert ok is False
        assert err is boom

    def test_missed_deadline_reports_timeout(self):
        import time

        ok, err = organize._run_bounded(lambda: time.sleep(5), 0.05)
        assert ok is False
        assert isinstance(err, TimeoutError)


class TestOrganizeDispatch:
    def test_anonymous_is_redirected_to_login(self):
        # Act
        for tab in ("usage", "duplicates", "move"):
            request = _request(AnonymousUser(), f"/apps/storage/?tab={tab}")
            response = storage_views.index(request)
            # Assert
            assert response.status_code == 302, tab
            assert "/auth/login/" in response["Location"], tab

    def test_usage_tab_renders_donut(self):
        # Arrange
        from scitex_storage._measure._scan import RootScan

        volume = _fake_volume()
        resolve, measure = _patch_volumes([volume], [_fake_status(volume)])
        request = _request(_user(), "/apps/storage/?tab=usage")
        # Act
        with (
            resolve,
            measure,
            mock.patch.object(
                scitex_storage,
                "scan",
                return_value=RootScan(root=Path("/tmp"), children=[]),
                create=True,
            ),
        ):
            response = storage_views.index(request)
        # Assert
        assert response.status_code == 200
        content = response.content.decode()
        assert "Where your bytes live" in content
        assert "?tab=usage" in content
        assert 'aria-selected="true"' in content

    def test_usage_unknown_volume_fails_closed(self):
        # Arrange
        volume = _fake_volume()
        resolve, measure = _patch_volumes([volume], [_fake_status(volume)])
        request = _request(_user(), "/apps/storage/?tab=usage&volume=no-such-volume")
        # Act
        with resolve, measure:
            response = storage_views.index(request)
        # Assert
        assert response.status_code == 403

    def test_duplicates_tab_is_read_only(self):
        # Arrange
        volume = _fake_volume()
        resolve, measure = _patch_volumes([volume], [_fake_status(volume)])
        request = _request(_user(), "/apps/storage/?tab=duplicates")
        # Act
        with (
            resolve,
            measure,
            mock.patch.object(
                scitex_storage, "find_duplicates", return_value=[], create=True
            ),
        ):
            response = storage_views.index(request)
        # Assert
        assert response.status_code == 200
        content = response.content.decode()
        assert "Read-only report" in content
        # No delete/resolve affordance anywhere on the page (hub chrome has
        # its own unrelated POST forms, so scope to storage action names).
        assert 'name="delete"' not in content
        assert 'name="resolve"' not in content

    def test_duplicates_unavailable_without_fclones(self):
        # Arrange
        from scitex_storage._measure._scan import MissingSystemDependencyError

        volume = _fake_volume()
        resolve, measure = _patch_volumes([volume], [_fake_status(volume)])
        request = _request(_user(), "/apps/storage/?tab=duplicates")
        # Act
        with (
            resolve,
            measure,
            mock.patch.object(
                scitex_storage,
                "find_duplicates",
                side_effect=MissingSystemDependencyError("no fclones"),
                create=True,
            ),
        ):
            response = storage_views.index(request)
        # Assert
        assert response.status_code == 200
        assert "fclones" in response.content.decode()

    def test_duplicates_lists_groups_with_reclaimable(self, tmp_path):
        # Arrange
        from scitex_storage._measure import _duplicates

        a = tmp_path / "a.bin"
        b = tmp_path / "b.bin"
        a.write_bytes(b"x" * 100)
        b.write_bytes(b"x" * 100)
        volume = _fake_volume(path=str(tmp_path))
        resolve, measure = _patch_volumes([volume], [_fake_status(volume)])
        request = _request(_user(), "/apps/storage/?tab=duplicates")
        # Act
        with (
            resolve,
            measure,
            mock.patch.object(
                scitex_storage,
                "find_duplicates",
                return_value=[[a, b]],
                create=True,
            ),
            mock.patch.object(_duplicates, "reclaimable_bytes", return_value=100),
        ):
            response = storage_views.index(request)
        # Assert
        assert response.status_code == 200
        content = response.content.decode()
        assert "duplicate groups" in content
        assert "a.bin" in content and "b.bin" in content

    def test_move_tab_shows_tiers_and_disabled_apply(self):
        # Arrange
        volume = _fake_volume()
        resolve, measure = _patch_volumes([volume], [_fake_status(volume)])
        request = _request(_user(), "/apps/storage/?tab=move")
        # Act
        with resolve, measure:
            response = storage_views.index(request)
        # Assert
        assert response.status_code == 200
        content = response.content.decode()
        assert "Plan a move" in content
        assert "Applying a move is disabled in the browser" in content
        # The plan form is a read-only GET; there is no apply affordance.
        assert '<form method="get"' in content
        assert 'name="apply"' not in content

    def test_move_plan_unknown_volume_fails_closed(self):
        # Arrange
        volume = _fake_volume()
        resolve, measure = _patch_volumes([volume], [_fake_status(volume)])
        request = _request(
            _user(),
            "/apps/storage/?tab=move&plan=1&volume=nope&dir=x&destination=scitex-nas-01",
        )
        # Act
        with resolve, measure:
            response = storage_views.index(request)
        # Assert
        assert response.status_code == 403

    def test_move_plan_path_escape_fails_closed(self):
        # Arrange
        volume = _fake_volume()
        resolve, measure = _patch_volumes([volume], [_fake_status(volume)])
        request = _request(
            _user(),
            "/apps/storage/?tab=move&plan=1&volume=workspace&dir=../../..&destination=scitex-nas-01",
        )
        # Act
        with resolve, measure:
            response = storage_views.index(request)
        # Assert
        assert response.status_code == 403

    def test_move_plan_renders_without_mutation(self, tmp_path):
        # Arrange
        (tmp_path / "sub").mkdir()
        volume = _fake_volume(path=str(tmp_path))
        resolve, measure = _patch_volumes([volume], [_fake_status(volume)])
        request = _request(
            _user(),
            "/apps/storage/?tab=move&plan=1&volume=workspace&dir=sub&destination=scitex-nas-01",
        )
        fake_plan = SimpleNamespace(
            source=str(tmp_path / "sub"),
            destination="scitex-nas-01",
            remote_path="/remote/sub",
            size_bytes=1234,
            file_count=7,
        )
        # Act
        with (
            resolve,
            measure,
            mock.patch.object(
                scitex_storage, "plan_archive", return_value=fake_plan, create=True
            ),
        ):
            response = storage_views.index(request)
        # Assert
        assert response.status_code == 200
        content = response.content.decode()
        assert "Move plan (not executed)" in content
        assert "scitex-nas-01" in content

    def test_backup_tab_stays_upstream_soon(self):
        # Arrange
        from scitex_storage._django import volumes as _volumes

        volume = _fake_volume()
        request = _request(_user(), "/apps/storage/?tab=backup")
        # Act: backup still delegates to the upstream view (real measure_all
        # over one fake volume is filesystem-only: statvfs on /tmp).
        with mock.patch.object(_volumes, "resolve_user_volumes", return_value=[volume]):
            response = storage_views.index(request)
        # Assert
        assert response.status_code == 200
        assert "Coming soon" in response.content.decode()


# EOF
