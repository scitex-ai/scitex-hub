"""A plugin cannot choose another user's persistent home."""
from types import SimpleNamespace
from pathlib import Path
import pytest
from django.core.exceptions import PermissionDenied
from apps.workspace.apps_app.services.plugin_volumes import (
    _checked_user_home, _user_home_name, user_home,
)

@pytest.mark.parametrize("name", [None, "", ".", "..", "../bob", "a/b", "a\\b", "a\0b"])
def test_unsafe_home_identity_is_refused(name):
    with pytest.raises(PermissionDenied):
        _user_home_name(name)

def test_anonymous_has_no_user_home():
    assert user_home(SimpleNamespace(user=SimpleNamespace(is_authenticated=False))) is None

def test_owned_home_is_resolved_without_creation(tmp_path):
    base = tmp_path / "users"
    home = base / "alice"
    assert _checked_user_home(base, home, "alice") == home
    assert not home.exists()

def test_another_user_home_is_refused(tmp_path):
    with pytest.raises(PermissionDenied):
        _checked_user_home(tmp_path, tmp_path / "bob", "alice")

def test_home_symlink_cannot_alias_another_user(tmp_path):
    (tmp_path / "bob").mkdir()
    (tmp_path / "alice").symlink_to(tmp_path / "bob", target_is_directory=True)
    with pytest.raises(PermissionDenied):
        _checked_user_home(tmp_path, tmp_path / "alice", "alice")

def test_home_symlink_cannot_escape(tmp_path):
    base = tmp_path / "users"
    base.mkdir()
    outside = tmp_path / "private"
    outside.mkdir()
    (base / "alice").symlink_to(outside, target_is_directory=True)
    with pytest.raises(PermissionDenied):
        _checked_user_home(base, base / "alice", "alice")


def test_looping_home_symlink_is_refused(tmp_path):
    (tmp_path / "alice").symlink_to(tmp_path / "alice", target_is_directory=True)
    with pytest.raises(PermissionDenied):
        _checked_user_home(tmp_path, tmp_path / "alice", "alice")
