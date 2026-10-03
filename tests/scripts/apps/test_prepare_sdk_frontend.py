"""Selected SDK frontend packaging; no Hub bootstrap, database or providers."""

import copy
import importlib.metadata
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import sys
import tarfile

import pytest

SCRIPT = Path(__file__).resolve().parents[3] / "scripts/apps/prepare_sdk_frontend.py"
SPEC = importlib.util.spec_from_file_location("prepare_sdk_frontend", SCRIPT)
frontend = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(frontend)


@pytest.fixture(scope="module")
def selected():
    return frontend.selected_frontend()


@pytest.fixture(scope="module")
def packed(tmp_path_factory):
    project = tmp_path_factory.mktemp("sdk-frontend-consumer")
    receipt = frontend.prepare(project)
    return project / ".frontend-packages/scitex-sdk.tgz", receipt


@pytest.mark.parametrize("version", ["0.3.0", "0.3.1", "1.0.0"])
def test_frontend_accepts_supported_stable_release(version):
    # Arrange
    expected = tuple(int(part) for part in version.split("."))

    # Act
    result = frontend._release_version(version)

    # Assert
    assert result == expected


@pytest.mark.parametrize("version", ["0.2.9", "0.3.0rc1", "0.3.0-dev", "3", "", None])
def test_frontend_refuses_unsatisfied_or_unsupported_release(version):
    # Arrange

    # Act
    with pytest.raises(ValueError, match="SDK frontend requires"):
        # Assert: the expected exception context verifies the refusal.
        frontend._release_version(version)


def test_selected_frontend_belongs_to_real_python_distribution(selected):
    # Arrange
    directory, metadata, _ = selected
    distribution = importlib.metadata.distribution("scitex-sdk")

    # Act
    frontend._owned_package(distribution, directory)

    # Assert
    assert metadata["version"] == distribution.version


def test_other_directory_cannot_impersonate_selected_distribution(tmp_path):
    # Arrange
    distribution = importlib.metadata.distribution("scitex-sdk")

    # Act
    with pytest.raises(ValueError, match="does not own"):
        # Assert: the expected exception context verifies the refusal.
        frontend._owned_package(distribution, tmp_path)


@pytest.mark.parametrize("key", ["./ui", "./ui/ts", "./ui/css/*"])
def test_missing_canonical_export_refuses_frontend(selected, key):
    # Arrange
    directory, original, _ = selected
    metadata = copy.deepcopy(original)
    del metadata["exports"][key]

    # Act
    with pytest.raises(ValueError, match="canonical frontend exports"):
        # Assert: the expected exception context verifies the refusal.
        frontend._frontend_files(directory, metadata)


def test_genuine_npm_archive_contains_exact_selected_frontend(selected, packed):
    # Arrange
    directory, metadata, expected = selected
    archive, receipt = packed

    # Act
    frontend.verify_archive(archive, directory, expected)

    # Assert
    assert receipt["version"] == metadata["version"]


def test_genuine_archive_preserves_declared_sdk_export_map(selected, packed):
    # Arrange
    _, metadata, _ = selected
    archive, _ = packed

    # Act
    with tarfile.open(archive, "r:gz") as content:
        actual = json.loads(content.extractfile("package/package.json").read())

    # Assert
    assert actual == metadata


@pytest.mark.parametrize("name", ["/package/package.json", "package/../package.json", "other/package.json"])
def test_unsafe_archive_path_is_refused(tmp_path, selected, name):
    # Arrange
    directory, _, expected = selected
    archive = _archive(tmp_path, name, b"{}")

    # Act
    with pytest.raises(ValueError, match="unsafe path"):
        # Assert: the expected exception context verifies the refusal.
        frontend.verify_archive(archive, directory, expected)


def test_archive_cannot_substitute_frontend_bytes(tmp_path, selected):
    # Arrange
    directory, _, expected = selected
    archive = _archive(tmp_path, "package/package.json", b"{}")

    # Act
    with pytest.raises(ValueError, match="differs"):
        # Assert: the expected exception context verifies the refusal.
        frontend.verify_archive(archive, directory, expected)


def test_archive_cannot_omit_required_frontend_assets(tmp_path, selected):
    # Arrange
    directory, _, expected = selected
    archive = _archive(tmp_path, "package/package.json", (directory / "package.json").read_bytes())

    # Act
    with pytest.raises(ValueError, match="omits"):
        # Assert: the expected exception context verifies the refusal.
        frontend.verify_archive(archive, directory, expected)


def test_archive_cannot_replay_a_duplicate_member(tmp_path, selected):
    # Arrange
    directory, _, _ = selected
    archive = _archive(tmp_path, "package/package.json", (directory / "package.json").read_bytes(), repeat=True)

    # Act
    with pytest.raises(ValueError, match="unique regular"):
        # Assert: the expected exception context verifies the refusal.
        frontend.verify_archive(archive, directory, [directory / "package.json"])


def test_real_absent_sdk_stops_before_npm_pack():
    # Arrange
    command = [sys.executable, "-I", "-S", "-B", str(SCRIPT)]

    # Act
    result = subprocess.run(command, capture_output=True, text=True, check=False)

    # Assert
    assert result.returncode == 1 and "SDK frontend preparation refused" in result.stderr


def test_installed_frontend_matches_genuine_selected_archive(tmp_path, selected, packed):
    # Arrange
    _, metadata, _ = selected
    project = _installed_fixture(tmp_path, packed[0])

    # Act
    result = frontend.verify_installed(project)

    # Assert
    assert result["version"] == metadata["version"]


@pytest.mark.parametrize("name", ["package.json", "ui/static/scitex_sdk/ui/css/app.css", "ui/static/scitex_sdk/ui/ts/index.ts"])
def test_installed_frontend_refuses_stale_source_bytes(tmp_path, packed, name):
    # Arrange
    project = _installed_fixture(tmp_path, packed[0])
    target = project / "node_modules/@scitex/sdk" / name
    target.write_bytes(target.read_bytes() + b"\nchanged")

    # Act
    with pytest.raises(ValueError, match="differs from selected Python SDK"):
        # Assert: the expected exception context verifies the refusal.
        frontend.verify_installed(project)


def test_missing_installed_frontend_is_refused(tmp_path):
    # Arrange

    # Act
    with pytest.raises(ValueError, match="missing or unsafe"):
        # Assert: the expected exception context verifies the refusal.
        frontend.verify_installed(tmp_path)


def test_external_sdk_link_is_refused(tmp_path, selected):
    # Arrange
    directory, _, _ = selected
    target = tmp_path / "node_modules/@scitex/sdk"
    target.parent.mkdir(parents=True)
    target.symlink_to(directory, target_is_directory=True)

    # Act
    with pytest.raises(ValueError, match="escapes the consumer"):
        # Assert: the expected exception context verifies the refusal.
        frontend.verify_installed(tmp_path)


def _installed_fixture(project, archive):
    root = project / "node_modules/@scitex/sdk"
    with tarfile.open(archive, "r:gz") as content:
        for member in content:
            if member.isfile():
                target = root / Path(member.name).relative_to("package")
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(content.extractfile(member).read())
    return project


def _archive(directory, name, data, repeat=False):
    archive = directory / "controlled.tgz"
    with tarfile.open(archive, "w:gz") as content:
        for _ in range(2 if repeat else 1):
            item = tarfile.TarInfo(name)
            item.size = len(data)
            content.addfile(item, io.BytesIO(data))
    return archive
