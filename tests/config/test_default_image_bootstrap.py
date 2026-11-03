"""Source/file controls complement the mandatory real image root-init smoke."""

import hashlib
import importlib.util
import os
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "default_bootstrap", ROOT / "scripts/deploy/verify_default_bootstrap.py"
)
BOOT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BOOT)


def test_image_constructor_precedes_actual_nested_mount_full_boot_gate():
    source = (ROOT / "deployment/docker/docker_prod/Dockerfile.prod").read_text()
    last_import = source.index("# Authoritative relationship gate.")
    constructor = source.index("# Finish image-owned mutable defaults")
    metadata = source.index("verify_default_bootstrap.py --constructor")
    boot = source.index("verify_default_bootstrap.py --full-root-init")
    assert (
        last_import < constructor < metadata < boot,
        "--mount=type=tmpfs,target=/app/data/users" in source,
        "--mount=type=tmpfs,target=/app/.scitex" in source,
    ) == (True, True, True)


def test_runtime_private_permission_guard_is_not_relaxed():
    path = ROOT / "deployment/docker/common/scripts/root-init.sh"
    assert hashlib.sha256(path.read_bytes()).hexdigest() == (
        "473f735a9a873fb0f54abce11b4ef53ca57bf4e5afad03429a51737cbc75b3fb"
    )


def test_constructor_accepts_owned_defaults_and_private_config(tmp_path):
    state = tmp_path / "state"
    state.mkdir(mode=0o700)
    config = state / "config"
    config.write_bytes(b"owned synthetic configuration")
    config.chmod(0o600)
    result = BOOT.constructor_metadata([state], [state], os.getuid(), os.getgid())
    assert result[str(config)] == {
        "uid": os.getuid(),
        "gid": os.getgid(),
        "mode": 0o600,
    }


def test_constructor_refuses_missing_default_parent(tmp_path):
    with pytest.raises(AssertionError):
        BOOT.constructor_metadata(
            [tmp_path / "absent"], [tmp_path / "absent"], os.getuid(), os.getgid()
        )


def test_constructor_refuses_root_or_foreign_owned_config_metadata(tmp_path):
    config = tmp_path / "config"
    config.write_bytes(b"owned fixture")
    with pytest.raises(AssertionError):
        BOOT.constructor_metadata([tmp_path], [tmp_path], os.getuid() + 1, os.getgid())


def test_constructor_refuses_symbolic_state(tmp_path):
    state = tmp_path / "state"
    state.mkdir()
    (state / "config").symlink_to(tmp_path / "outside")
    with pytest.raises(AssertionError):
        BOOT.constructor_metadata([state], [state], os.getuid(), os.getgid())
