"""Real key creation, persistence, permissions and concurrent initialization."""

from concurrent.futures import ThreadPoolExecutor
from contextlib import chdir
import os
from pathlib import Path
import stat
from threading import Barrier

from django.test import override_settings
import paramiko
import pytest

from apps.infra.workspace_app.services.ssh_key_manager import SSHKeyManager


@pytest.fixture
def owned_state(tmp_path):
    previous = os.environ.get("SCITEX_DIR")
    os.environ["SCITEX_DIR"] = str(tmp_path / "state")
    try:
        with chdir(tmp_path):
            yield tmp_path / "state"
    finally:
        if previous is None:
            os.environ.pop("SCITEX_DIR", None)
        else:
            os.environ["SCITEX_DIR"] = previous


def _failure(manager):
    try:
        manager.load_or_generate_host_key()
    except (OSError, paramiko.SSHException, ValueError) as error:
        return type(error).__name__
    return None


def test_default_key_reuses_configured_state_across_working_directories(owned_state):
    # Arrange
    with override_settings(SSH_KEY_DIR=None):
        first = SSHKeyManager()
        key = first.load_or_generate_host_key()
        replacement = Path.cwd() / "replacement-code"
        replacement.mkdir()
        # Act
        with chdir(replacement):
            second = SSHKeyManager()
            reopened = second.load_or_generate_host_key()
        observed = (first.key_dir, second.key_dir, key.asbytes() == reopened.asbytes())
    # Assert
    assert observed == (
        owned_state / "hub/runtime/ssh",
        owned_state / "hub/runtime/ssh",
        True,
    )


def test_explicit_directory_wins_over_host_setting(tmp_path):
    # Arrange
    explicit = tmp_path / "explicit"
    # Act
    with override_settings(SSH_KEY_DIR=tmp_path / "configured"):
        manager = SSHKeyManager(key_dir=explicit)
    # Assert
    assert manager.key_dir == explicit


def test_host_setting_is_respected(tmp_path):
    # Arrange
    configured = tmp_path / "configured"
    # Act
    with override_settings(SSH_KEY_DIR=configured):
        manager = SSHKeyManager()
    # Assert
    assert manager.key_dir == configured


def test_generated_key_and_directory_are_private(tmp_path):
    # Arrange
    directory = tmp_path / "keys"
    manager = SSHKeyManager(key_dir=directory)
    # Act
    manager.load_or_generate_host_key()
    observed = (
        stat.S_IMODE(directory.stat().st_mode),
        stat.S_IMODE(manager.get_host_key_path().stat().st_mode),
    )
    # Assert
    assert observed == (0o700, 0o600)


def test_invalid_existing_key_is_refused_without_replacement(tmp_path):
    # Arrange
    manager = SSHKeyManager(key_dir=tmp_path)
    path = manager.get_host_key_path()
    original = b"invalid owned test key\n"
    path.write_bytes(original)
    path.chmod(0o600)
    # Act
    failure = _failure(manager)
    observed = (failure is not None, path.read_bytes())
    # Assert
    assert observed == (True, original)


def test_unreadable_key_does_not_create_an_ephemeral_identity(tmp_path):
    # Arrange
    manager = SSHKeyManager(key_dir=tmp_path)
    path = manager.get_host_key_path()
    paramiko.RSAKey.generate(2048).write_private_key_file(str(path))
    path.chmod(0)
    try:
        # Act
        failure = _failure(manager)
        # Assert
        assert failure == "PermissionError"
    finally:
        path.chmod(0o600)


def test_group_readable_key_is_refused(tmp_path):
    # Arrange
    manager = SSHKeyManager(key_dir=tmp_path)
    path = manager.get_host_key_path()
    paramiko.RSAKey.generate(2048).write_private_key_file(str(path))
    path.chmod(0o640)
    # Act
    failure = _failure(manager)
    # Assert
    assert failure == "PermissionError"


def test_symbolic_key_is_refused_without_changing_its_target(tmp_path):
    # Arrange
    directory = tmp_path / "keys"
    manager = SSHKeyManager(key_dir=directory)
    target = tmp_path / "other-key"
    paramiko.RSAKey.generate(2048).write_private_key_file(str(target))
    original = target.read_bytes()
    manager.get_host_key_path().symlink_to(target)
    # Act
    failure = _failure(manager)
    observed = (
        failure is not None,
        target.read_bytes(),
        manager.get_host_key_path().is_symlink(),
    )
    # Assert
    assert observed == (True, original, True)


def test_concurrent_initializers_publish_one_reopenable_key(tmp_path):
    # Arrange
    directory = tmp_path / "keys"
    barrier = Barrier(4)

    def initialize(_):
        manager = SSHKeyManager(key_dir=directory)
        barrier.wait(timeout=10)
        return manager.load_or_generate_host_key().asbytes()

    # Act
    with ThreadPoolExecutor(max_workers=4) as pool:
        keys = list(pool.map(initialize, range(4)))
    reopened = SSHKeyManager(key_dir=directory).load_or_generate_host_key().asbytes()
    # Assert
    assert set(keys) == {reopened}
