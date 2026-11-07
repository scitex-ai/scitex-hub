"""Execute the real bootstrap directory admission against owned filesystem trees."""

import os
import re
import stat
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "deployment/docker/common/scripts/root-init.sh"


def directory_functions():
    source = SCRIPT.read_text()
    names = (
        "bootstrap_directory_accessible",
        "prepare_bootstrap_directory",
        "prepare_bootstrap_directories",
    )
    return "\n".join(
        re.search(rf"^{name}\(\) \{{\n.*?^\}}", source, re.M | re.S).group()
        for name in names
    )


def prepare(root):
    return subprocess.run(
        [
            "bash",
            "-c",
            directory_functions() + '\nprepare_bootstrap_directories "$1" "$2" "$3"',
            "owned-bootstrap",
            str(root),
            str(os.getuid()),
            str(os.getgid()),
        ],
        capture_output=True,
        text=True,
        timeout=10,
    )


def snapshot(root):
    result = {}
    for path in [root, *sorted(root.rglob("*"))]:
        info = path.lstat()
        result[str(path.relative_to(root))] = (
            stat.S_IMODE(info.st_mode),
            info.st_uid,
            info.st_gid,
            path.read_bytes() if path.is_file() and not path.is_symlink() else None,
        )
    return result


@pytest.mark.parametrize("directory_mode", [0o700, 0o750, 0o770])
def test_private_user_and_config_descendants_are_unchanged(tmp_path, directory_mode):
    root = tmp_path / "app"
    user = root / "data/users/owned/project"
    config = root / ".scitex/private"
    for path in [user, config]:
        path.mkdir(parents=True)
        path.chmod(directory_mode)
        private = path / "private.txt"
        private.write_bytes(b"owned fixture; never a credential")
        private.chmod(0o600)
    (root / "data/users").chmod(0o700)
    (root / ".scitex").chmod(0o700)
    before = snapshot(root)
    run = prepare(root)
    after = snapshot(root)
    observed = {name: after[name] for name in before}
    assert (run.returncode, observed) == (0, before), run.stderr


def test_new_directory_tree_is_private_and_application_owned(tmp_path):
    run = prepare(tmp_path)
    directories = [p for p in tmp_path.rglob("*") if p.is_dir()]
    observed = {
        (stat.S_IMODE(p.stat().st_mode), p.stat().st_uid, p.stat().st_gid)
        for p in directories
    }
    assert (run.returncode, len(directories), observed) == (
        0,
        10,
        {(0o700, os.getuid(), os.getgid())},
    ), run.stderr


@pytest.mark.parametrize("relative", ["data", "data/users", ".scitex", ".scitex/hub"])
def test_symbolic_directory_is_refused_without_touching_target(tmp_path, relative):
    root = tmp_path / "app"
    root.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir(mode=0o700)
    private = outside / "private.txt"
    private.write_bytes(b"owned outside sentinel")
    private.chmod(0o600)
    target = root / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    target.symlink_to(outside, target_is_directory=True)
    before = snapshot(outside)
    run = prepare(root)
    assert (run.returncode != 0, snapshot(outside), target.is_symlink()) == (
        True,
        before,
        True,
    )


def test_non_directory_user_mount_is_refused(tmp_path):
    (tmp_path / "data").mkdir()
    target = tmp_path / "data/users"
    target.write_bytes(b"owned nondirectory")
    before = snapshot(target)
    run = prepare(tmp_path)
    assert (run.returncode != 0, snapshot(target)) == (True, before)


def test_actual_startup_admits_only_explicit_directory_metadata():
    source = SCRIPT.read_text()
    unsafe = re.search(
        r"(?:chmod|chown)\s+-R[^\n]*(?:/app/data(?:\s|$)|/app/data/users|/app/\.scitex)",
        source,
    )
    assert (
        unsafe,
        'gosu "$app_uid" sh -c' in source,
        'gosu "$app_uid:$app_gid"' in source,
        'prepare_bootstrap_directories /app "$(id -u scitex)" "$(id -g scitex)"'
        in source,
    ) == (None, True, False, True)
