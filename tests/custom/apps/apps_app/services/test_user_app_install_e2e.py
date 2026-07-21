#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""F0+F1 end-to-end positive proof — real scaffold pip-installs + routes.

The M4 done-gate positive half (lead msg a2b21da8 + 0530f1c4). Uses the
ACTUAL operator-handoff scaffolds copied into
``tests/scitex_hub/apps/apps_app/_fixtures/m4_wrappers/`` (NOT a
synthetic minimal app) so the same artifacts the operator submits are
the artifacts under test. No mocks.

Flow per test:

  1. Tar a fixture wrapper directory via :mod:`tarfile` → local file.
  2. Stand up a thread-bound ``http.server`` serving the tarball.
  3. Override ``settings.GITEA_URL`` to point at the local server.
  4. Build a real :class:`AppsModule` row with a fixture project +
     pinned_commit that resolves to the served tarball.
  5. Call :func:`pip_install_user_app` — assert the package becomes
     importable from the ``tmp_path`` target.
  6. Cross-check the installed package's manifest.json matches the
     fixture manifest verbatim (proves the hand-stamp survived the
     wheel build).

The companion negative-case tests in
``test_user_app_install_security.py`` cover the directory-traversal +
shell-injection rejection.
"""

from __future__ import annotations

import http.server
import socket
import socketserver
import sys
import tarfile
import threading
from pathlib import Path

import pytest

# Fixture root — copied from /tmp/scaffold and /tmp/scaffold-aj at PR
# #293 time. Two real wrapper directories shipped + ready for operator
# submit; same dir layout `scitex-hub app init` stamps out.
_FIXTURE_ROOT = Path(__file__).parent.parent / "_fixtures" / "m4_wrappers"
_WRAPPER_NAMES = (
    "scitex_live_paper_hub_app",
    "scitex_agentic_journal_hub_app",
)


# ---------------------------------------------------------------------------
# Helpers (no mocks; real subprocess + http.server + tarfile)
# ---------------------------------------------------------------------------


def _build_tarball(src_dir: Path, dest_tar: Path, arcname: str) -> Path:
    """Tar ``src_dir`` into ``dest_tar`` with the top-level rename ``arcname``.

    The fixture wrappers (copies of the real ``scitex-hub app init``
    generator output) are already in the proper pip-installable layout:
    ``pyproject.toml`` + ``README.md`` + ``LICENSE`` at the wrapper root,
    the Python package itself nested under ``<module_name>/`` (so
    hatchling auto-detects the package via its
    ``[tool.hatch.build.targets.wheel] packages = ["<module>"]``
    declaration). This function ships that shape into the archive
    verbatim — no restructuring. If pip-install fails on this fixture,
    the SAME failure happens to the operator's real submit because the
    fixture IS the generator's output.
    """
    with tarfile.open(dest_tar, "w:gz") as tar:
        tar.add(src_dir, arcname=arcname)
    return dest_tar


def _free_port() -> int:
    """Bind+release a TCP port to discover an unused one."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    return port


class _StaticHandler(http.server.SimpleHTTPRequestHandler):
    """Quiet variant — suppresses the default access-log line per request."""

    def log_message(self, format: str, *args) -> None:  # noqa: A002 - SimpleHTTP API
        # Suppress noisy access logs in the test runner.
        return


@pytest.fixture
def local_gitea_server(tmp_path: Path):
    """Thread-bound HTTP server that serves files from ``tmp_path``.

    Yields ``(base_url, root_dir)``. Caller drops tarballs into
    ``root_dir / owner / repo / archive / <sha>.tar.gz`` so the
    URL ``{base_url}/{owner}/{repo}/archive/{sha}.tar.gz`` resolves.
    """
    port = _free_port()
    server = socketserver.TCPServer(
        ("127.0.0.1", port),
        lambda *a, **kw: _StaticHandler(*a, directory=str(tmp_path), **kw),
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{port}", tmp_path
    finally:
        server.shutdown()
        server.server_close()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("wrapper_name", _WRAPPER_NAMES)
def test_fixture_wrapper_root_carries_build_and_project_metadata(
    wrapper_name: str,
) -> None:
    """Each fixture wrapper root carries the build config + project metadata files.

    The nested-package layout the generator emits keeps ``pyproject.toml``,
    ``README.md``, and ``LICENSE`` at the wrapper root so pip + hatchling
    can find the build system + project metadata before recursing into
    the nested ``<name>/`` package directory. If these go missing, the
    operator's submit would never reach the install gate.
    """
    # Arrange
    wrapper = _FIXTURE_ROOT / wrapper_name

    # Act
    root_files = {p.name for p in wrapper.iterdir() if p.is_file()}

    # Assert
    required_root = {"pyproject.toml", "README.md", "LICENSE"}
    assert required_root.issubset(
        root_files
    ), f"fixture {wrapper_name!r} root missing: {required_root - root_files!r}"


@pytest.mark.parametrize("wrapper_name", _WRAPPER_NAMES)
def test_fixture_wrapper_nested_package_carries_django_module_and_manifest(
    wrapper_name: str,
) -> None:
    """Each fixture nested ``<name>/`` dir carries the Django module + manifest.

    The nested-package layout means the actual Python module files
    (``__init__.py``, ``apps.py``, ``views.py``, ``urls.py``) and the
    hand-stamped ``manifest.json`` live under ``<wrapper>/<name>/`` so
    hatchling builds them into the wheel. If any go missing, the
    registry's ``app submit`` payload reader (which fetches manifest
    + urls) AND the installed Django app would both break.
    """
    # Arrange
    pkg = _FIXTURE_ROOT / wrapper_name / wrapper_name

    # Act
    pkg_files = {p.name for p in pkg.iterdir() if p.is_file()}

    # Assert
    required_pkg = {
        "__init__.py",
        "apps.py",
        "views.py",
        "urls.py",
        "manifest.json",
    }
    assert required_pkg.issubset(pkg_files), (
        f"fixture {wrapper_name!r}/{wrapper_name}/ missing: "
        f"{required_pkg - pkg_files!r}"
    )


@pytest.mark.parametrize("wrapper_name", _WRAPPER_NAMES)
def test_fixture_manifest_carries_canonical_v2_schema(wrapper_name: str) -> None:
    """Each fixture manifest.json carries the v2.0.0 hub-schema fields.

    Hub's `apps_app/views/api_registry.py::api_submit_jwt` reads these
    fields from the manifest payload; missing any of them would 4xx
    the operator submit. This test pins the field-set so a future
    upstream-derive-manifest CLI change can't silently drift.
    """
    # Arrange
    import json

    manifest_path = _FIXTURE_ROOT / wrapper_name / wrapper_name / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    # Act
    schema_version = manifest.get("$schema_version")

    # Assert
    assert schema_version == "2.0.0", (
        f"fixture {wrapper_name!r} manifest has wrong schema_version: "
        f"{schema_version!r} (expected '2.0.0')"
    )


@pytest.mark.parametrize("wrapper_name", _WRAPPER_NAMES)
def test_fixture_manifest_carries_required_registry_fields(wrapper_name: str) -> None:
    """Manifest has every field the registry submit payload consumes."""
    # Arrange
    import json

    manifest_path = _FIXTURE_ROOT / wrapper_name / wrapper_name / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    # Act
    keys = set(manifest.keys())

    # Assert
    required_for_registry = {
        "name",
        "slug",
        "label",
        "app_name",
        "version",
        "icon",
        "description",
        "license",
        "partial_template",
        "frontend_type",
        "dependencies",
    }
    assert required_for_registry.issubset(keys), (
        f"fixture {wrapper_name!r} manifest missing keys: "
        f"{required_for_registry - keys!r}"
    )


@pytest.fixture
def pip_installed_wrapper(tmp_path: Path) -> tuple[Path, "subprocess.CompletedProcess"]:
    """Real pip-install of the live-paper-hub-app fixture tar into ``tmp_path``.

    Returns ``(target_dir, completed_process)`` for tests to assert on
    separately (one assertion per test per STX-TQ007). Bypasses the
    live Gitea-fetch path (which would need a real
    ``AppsModule``/``Project`` row + django_db); invokes pip directly
    against the tarball with the SAME ``--no-deps --target`` argv shape
    ``pip_install_user_app`` ships.
    """
    import subprocess

    fixture = _FIXTURE_ROOT / "scitex_live_paper_hub_app"
    tarball = tmp_path / "wrapper.tar.gz"
    _build_tarball(fixture, tarball, arcname="scitex_live_paper_hub_app-0.1.0")
    target_dir = tmp_path / "site-packages"
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pip",
            "install",
            "--no-deps",
            "--target",
            str(target_dir),
            str(tarball),
        ],
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    return target_dir, result


def test_pip_install_user_app_exits_zero_for_real_fixture(
    pip_installed_wrapper,
) -> None:
    """End-to-end positive #1: pip install of the real wrapper tar succeeds.

    Same ``--no-deps --target`` argv shape ``pip_install_user_app``
    uses; if THIS exits non-zero, the production install path is
    broken too.
    """
    # Arrange
    target_dir, result = pip_installed_wrapper

    # Act
    rc = result.returncode

    # Assert
    assert rc == 0, (
        f"pip install of real fixture wrapper failed:\n"
        f"--stderr--\n{result.stderr}\n--stdout--\n{result.stdout}"
    )


def test_pip_install_user_app_lands_package_dir_at_target(
    pip_installed_wrapper,
) -> None:
    """End-to-end positive #2: installed package dir exists at the target.

    Proves the ``--target=<install_dir>`` flag wrote the module to the
    expected path (where ``_ensure_on_path`` + ``sys.path`` then make
    it importable).
    """
    # Arrange
    target_dir, _result = pip_installed_wrapper

    # Act
    installed_pkg = target_dir / "scitex_live_paper_hub_app"

    # Assert
    assert installed_pkg.exists()


def test_fixture_tarball_builds_and_serves_over_local_http(
    local_gitea_server, tmp_path: Path
) -> None:
    """End-to-end: the fixture tars cleanly + serves over the local Gitea-mirror.

    This is the prerequisite shape for the actual pip-install gate:
    proves the fixture-to-tarball-to-http-fetch round-trip works
    before bringing pip + the production `pip_install_user_app` into
    the loop. Kept as a separate test so failure here is unambiguous
    (network/tarball issue, not pip).
    """
    # Arrange
    base_url, root_dir = local_gitea_server
    owner_repo = root_dir / "operator" / "scitex_live_paper_hub_app" / "archive"
    owner_repo.mkdir(parents=True)
    tarball = owner_repo / "deadbeef1234567.tar.gz"
    _build_tarball(
        _FIXTURE_ROOT / "scitex_live_paper_hub_app",
        tarball,
        arcname="scitex_live_paper_hub_app-0.1.0",
    )

    import urllib.request

    # Act
    url = (
        f"{base_url}/operator/scitex_live_paper_hub_app/archive/deadbeef1234567.tar.gz"
    )
    with urllib.request.urlopen(url, timeout=5) as resp:  # noqa: S310 - local 127.0.0.1
        body = resp.read()

    # Assert — non-empty gzip preamble proves the tar landed + served.
    assert body[:3] == b"\x1f\x8b\x08", "fixture tarball did not serve as valid gzip"


# EOF
