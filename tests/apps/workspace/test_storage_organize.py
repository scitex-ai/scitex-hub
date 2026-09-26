"""Storage mount contract — the leaf owns its UI, the hub owns the wiring.

scitex-storage's Django app (``index`` + the Usage/Duplicates/Move tabs in
``scitex_storage._django.organize``) is served EXCLUSIVELY through the
generic plugin mount. The hub-side wrapper (``storage_app`` views/urls/
organize/volumes) is deleted. Nothing here tests leaf internals — this
file pins the CONTRACT between host and leaf:

- thin-hub: no wrapper files, and the volumes-provider setting points at
  the generic provider;
- the mount: /apps/storage/ resolves to the leaf namespace, and the leaf
  manifest declares the login boundary (leaf installed; otherwise those
  tests skip with a reason);
- the wiring, DB-free: the leaf's ``resolve_user_volumes`` served through
  the hub provider hands the requester exactly their own volumes (and
  nothing for anonymous);
- the containment primitives the leaf view refuses with: an unknown
  volume key resolves to ``None`` (the view answers 403) and a directory
  escaping its volume raises ``OutsideVolume`` (the view answers 403).
  There is no free-form path: every directory is resolved inside a volume
  the requester owns.

DB-free by design (this dev container's database role cannot create test
databases): stub users, ``ComputeIdentity.objects`` stubbed with
``unittest.mock``, no ORM.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import pytest
from django.test import RequestFactory

REPO_ROOT = Path(__file__).resolve().parents[3]
STORAGE_WRAPPER_ROOT = REPO_ROOT / "apps/workspace/storage_app"

RF = RequestFactory()


def _user(name="org_test"):
    return SimpleNamespace(username=name, is_authenticated=True)


def _leaf_volumes():
    return pytest.importorskip(
        "scitex_storage._django.volumes", reason="scitex-storage not installed"
    )


def _no_compute_identity():
    from apps.workspace.console_app.models import ComputeIdentity

    manager = mock.Mock()
    manager.filter.return_value.first.return_value = None
    return mock.patch.object(ComputeIdentity, "objects", manager)


# =====================================================================
# Thin-hub: the wrapper is gone, the provider setting is generic
# =====================================================================
def test_no_hub_side_storage_wrapper_files():
    # Arrange / Act
    leftovers = (
        sorted(p.name for p in STORAGE_WRAPPER_ROOT.glob("*") if p.is_file())
        if STORAGE_WRAPPER_ROOT.exists()
        else []
    )

    # Assert
    assert leftovers == [], f"hub-side storage wrapper files still present: {leftovers}"
    assert "storage_app" not in (REPO_ROOT / "config/urls.py").read_text()


def test_volumes_provider_setting_points_at_the_generic_provider():
    # Arrange / Act
    from django.conf import settings

    # Assert — the leaf asks the hub which directories belong to the
    # requester through generic hub infrastructure, never a per-app module.
    assert (
        settings.SCITEX_STORAGE_VOLUMES_PROVIDER
        == "apps.workspace.apps_app.services.plugin_volumes.user_volumes"
    )


# =====================================================================
# The mount serves the leaf (leaf installed)
# =====================================================================
def test_storage_root_url_resolves_to_the_leaf_namespace():
    # Arrange
    pytest.importorskip("scitex_storage._django.urls", reason="scitex-storage not installed")
    from django.urls import resolve

    # Act
    match = resolve("/apps/storage/")

    # Assert
    assert match.view_name.startswith("scitex_storage:")


def test_leaf_manifest_declares_the_login_boundary():
    # Arrange — the generic mount login-wraps the whole tree because the
    # LEAF asks for it in its own manifest (no hub-side wrapper).
    import importlib.util
    import json

    spec = importlib.util.find_spec("scitex_storage._django")
    if spec is None or not spec.origin:
        pytest.skip("scitex-storage not installed")

    # Act
    manifest = json.loads((Path(spec.origin).parent / "manifest.json").read_text())

    # Assert
    assert manifest.get("mount_policy", {}).get("login_required") is True


def test_leaf_owns_the_organize_tabs():
    # Arrange — Usage/Duplicates/Move are real leaf views (storage #96);
    # the hub deleted its organize.py rather than shadowing them.
    organize = pytest.importorskip(
        "scitex_storage._django.organize", reason="scitex-storage not installed"
    )

    # Act / Assert
    assert set(organize.HANDLED_TABS) >= {"usage", "duplicates", "move"}


# =====================================================================
# The wiring: resolve_user_volumes through the hub provider (DB-free)
# =====================================================================
def test_requester_gets_exactly_their_own_volumes():
    # Arrange
    _volumes = _leaf_volumes()
    request = RF.get("/apps/storage/")
    request.user = _user("vol_alice")

    # Act
    with _no_compute_identity():
        volumes = _volumes.resolve_user_volumes(request)

    # Assert — the workspace volume is her own data root; nothing else.
    assert [v.key for v in volumes] == ["workspace"]
    assert str(volumes[0].path).endswith("/data/users/vol_alice")


def test_anonymous_gets_no_volumes_from_the_leaf_resolver():
    # Arrange
    from django.contrib.auth.models import AnonymousUser

    _volumes = _leaf_volumes()
    request = RF.get("/apps/storage/")
    request.user = AnonymousUser()

    # Act
    volumes = _volumes.resolve_user_volumes(request)

    # Assert
    assert volumes == []


# =====================================================================
# The containment primitives the leaf refuses with (no render, no DB)
# =====================================================================
def test_unknown_volume_key_resolves_to_none():
    # Arrange — the leaf answers 403 when find_volume finds nothing.
    _volumes = _leaf_volumes()
    volume = _volumes.Volume(
        key="workspace", label="Workspace files", path=Path("/tmp"), machine="test"
    )

    # Act
    found = _volumes.find_volume([volume], "no-such-volume")

    # Assert
    assert found is None


def test_directory_escape_raises_outside_volume(tmp_path):
    # Arrange
    _volumes = _leaf_volumes()
    volume = _volumes.Volume(
        key="workspace", label="Workspace files", path=tmp_path, machine="test"
    )

    # Act / Assert — ../../.. never resolves; the leaf answers 403.
    with pytest.raises(_volumes.OutsideVolume):
        _volumes.contained_dir(volume, "../../..")


def test_in_volume_directory_resolves(tmp_path):
    # Arrange
    _volumes = _leaf_volumes()
    (tmp_path / "sub").mkdir()
    volume = _volumes.Volume(
        key="workspace", label="Workspace files", path=tmp_path, machine="test"
    )

    # Act
    resolved = _volumes.contained_dir(volume, "sub")

    # Assert
    assert resolved == (tmp_path / "sub").resolve()


# EOF
