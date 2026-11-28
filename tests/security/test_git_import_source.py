"""Regression: project import may only clone public repositories.

Project creation ("import from Git") and the repository tool hand a
tenant-supplied URL to ``git clone``. ``git`` also accepts local paths,
``file://`` URLs, other transports, internal hosts and ``-``-prefixed
arguments, so the source is validated by
``apps.infra.project_app.git_source_safety`` and the clone itself runs with
transports restricted, ``--`` before the URL, symlinks checked out as files,
a timeout and a size cap.

Tests use real git against local fixture repositories, the real Django test
client for the project-creation view, and resolver/connector fakes passed as
arguments to the production API (the same seams ``url_safety`` exposes). No
mocks, no outside network.
"""

from __future__ import annotations

import contextlib
import http.server
import os
import socket
import subprocess
import threading
from pathlib import Path

import pytest

from apps.infra.project_app.git_source_safety import (
    GitSource,
    GitSourceRejected,
    _follow_redirects,
    git_clone_command,
    run_git_clone,
    validate_git_source,
)
from apps.infra.project_app.url_safety import _resolve_public_addresses

pytestmark = pytest.mark.security

PUBLIC_TEST_IP = "93.184.216.34"


def _public_resolver(host, port):
    """Resolve the reserved test host names to a public-looking address and
    everything else through the production resolver."""
    if host.endswith(".test"):
        return [(socket.AF_INET, PUBLIC_TEST_IP)]
    return _resolve_public_addresses(host, port)


def _git(*args, cwd=None):
    subprocess.run(
        [
            "git",
            "-c",
            "user.name=t",
            "-c",
            "user.email=t@example.invalid",
            "-c",
            "core.hooksPath=/dev/null",
            "-c",
            "commit.gpgsign=false",
            *args,
        ],
        cwd=cwd,
        check=True,
        capture_output=True,
    )


@pytest.fixture
def fixture_repo(tmp_path):
    repo = tmp_path / "fixture-repo"
    repo.mkdir()
    _git("init", "-q", str(repo))
    (repo / "README.md").write_text("fixture\n")
    os.symlink("/etc/hostname", repo / "link")
    _git("add", "-A", cwd=repo)
    _git("commit", "-q", "-m", "init", cwd=repo)
    return repo


# --------------------------------------------------------------------------- #
# validate_git_source — forms that must be refused                             #
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    "url",
    [
        "/app/data/users/other/proj/slug",
        "../other/proj/slug",
        "file:///app/data/users/other/proj/slug",
        "ext::sh -c touch% /tmp/x",
        "--upload-pack=touch /tmp/x",
        "-uhack",
        "http://github.com/owner/repo.git",
        "git://github.com/owner/repo.git",
        "https://127.0.0.1/owner/repo.git",
        "https://localhost/owner/repo.git",
        "https://169.254.169.254/owner/repo.git",
        "https://10.0.0.5/owner/repo.git",
        "https://[::1]/owner/repo.git",
        "https://user:pw@github.com/owner/repo.git",
        "https://github.com/owner/repo.git?x=1",
        "https://github.com/-owner/repo.git",
        "https://github.com/owner/../../repo.git",
        "git@evil.example:owner/repo.git",
        "ssh://git@127.0.0.1/owner/repo.git",
        "ssh://-oProxyCommand=touch%20x/owner/repo",
        "root@github.com:owner/repo.git",
        "git@github.com:-oProxyCommand=x/repo",
        "https://github.com/owner/repo.git\n--upload-pack=x",
    ],
)
def _refusal(call, *args, **kwargs):
    """Return the GitSourceRejected raised by ``call``, or None."""
    try:
        call(*args, **kwargs)
    except GitSourceRejected as exc:
        return exc
    return None


def test_rejects_unsafe_source(url):
    # Arrange
    kwargs = {"follow_redirects": False}
    # Act
    refusal = _refusal(validate_git_source, url, **kwargs)
    # Assert
    assert isinstance(refusal, GitSourceRejected)


def test_rejects_host_outside_https_allowlist_before_network():
    # Arrange
    url = "https://forge.test/owner/repo.git"
    # Act
    refusal = _refusal(
        validate_git_source,
        url,
        https_hosts=("github.com",),
        _resolver=_public_resolver,
        follow_redirects=False,
    )
    # Assert
    assert isinstance(refusal, GitSourceRejected)


# --------------------------------------------------------------------------- #
# validate_git_source — accepted forms                                         #
# --------------------------------------------------------------------------- #
def test_accepts_scp_like_ssh_to_allowlisted_forge():
    # Arrange
    # Act
    source = validate_git_source("git@github.com:owner/repo.git")
    # Assert
    assert (source.protocol, source.host) == ("ssh", "github.com")


def test_accepts_ssh_url_to_allowlisted_forge():
    # Arrange
    # Act
    source = validate_git_source("ssh://git@gitlab.com/group/sub/repo.git")
    # Assert
    assert source.protocol == "ssh"


def test_https_source_is_pinned_to_the_validated_address():
    # Arrange
    source = validate_git_source(
        "https://forge.test/owner/repo.git",
        _resolver=_public_resolver,
        follow_redirects=False,
        # Act
    )
    # Assert
    assert source.pin == f"forge.test:443:{PUBLIC_TEST_IP}"


def test_clone_command_ends_options_before_the_url():
    # Arrange
    source = GitSource(
        url="https://forge.test/o/r.git", protocol="https", host="forge.test"
    )
    # Act
    cmd = git_clone_command(source, Path("/tmp/dest"))
    # Assert
    assert cmd[-3:] == ["--", "https://forge.test/o/r.git", "/tmp/dest"]


def test_clone_command_disables_other_transports_and_redirects():
    # Arrange
    source = GitSource(
        url="https://forge.test/o/r.git", protocol="https", host="forge.test"
    )
    # Act
    cmd = git_clone_command(source, Path("/tmp/dest"))
    # Assert
    assert {
        "protocol.allow=never",
        "protocol.https.allow=always",
        "http.followRedirects=false",
    } <= set(cmd)


# --------------------------------------------------------------------------- #
# Redirects are re-validated hop by hop                                        #
# --------------------------------------------------------------------------- #
class _RedirectHandler(http.server.BaseHTTPRequestHandler):
    target = ""

    def do_GET(self):  # noqa: N802 - stdlib handler API
        self.send_response(302)
        self.send_header("Location", self.target)
        self.end_headers()

    def log_message(self, *args):
        pass


@contextlib.contextmanager
def _redirect_server(target):
    handler = type("H", (_RedirectHandler,), {"target": target})
    server = http.server.HTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server.server_address[1]
    finally:
        server.shutdown()
        server.server_close()


def _loopback_connector(port):
    def connect(address, timeout=None, source_address=None, socket_options=None):
        return socket.create_connection(("127.0.0.1", port), timeout)

    return connect


def test_redirect_to_internal_address_is_refused():
    # Arrange
    internal = "http://127.0.0.1:3000/owner/repo.git/info/refs"
    # Act
    with _redirect_server(internal) as port:
        refusal = _refusal(
            _follow_redirects,
            "http://forge.test/owner/repo.git",
            _public_resolver,
            _loopback_connector(port),
        )
    # Assert
    assert isinstance(refusal, GitSourceRejected)


# --------------------------------------------------------------------------- #
# run_git_clone — real git against local fixtures                              #
# --------------------------------------------------------------------------- #
def test_file_transport_is_refused_by_git_even_without_validation(
    fixture_repo, tmp_path
):
    # Arrange
    source = GitSource(url=f"file://{fixture_repo}", protocol="https", host="")
    # Act
    ok, _reason = run_git_clone(source, tmp_path / "dest")
    # Assert
    assert ok is False


def test_local_path_is_refused_by_git_even_without_validation(fixture_repo, tmp_path):
    # Arrange
    source = GitSource(url=str(fixture_repo), protocol="https", host="")
    # Act
    ok, _reason = run_git_clone(source, tmp_path / "dest")
    # Assert
    assert ok is False


def test_failed_clone_leaves_no_destination(fixture_repo, tmp_path):
    # Arrange
    source = GitSource(url=f"file://{fixture_repo}", protocol="https", host="")
    # Act
    run_git_clone(source, tmp_path / "dest")
    # Assert
    assert not (tmp_path / "dest").exists()


def test_enabled_transport_clones_the_fixture(fixture_repo, tmp_path):
    # Arrange
    source = GitSource(url=f"file://{fixture_repo}", protocol="file", host="")
    # Act
    ok, _reason = run_git_clone(source, tmp_path / "dest")
    # Assert
    assert ok and (tmp_path / "dest" / "README.md").read_text() == "fixture\n"


def test_symlinks_are_checked_out_as_plain_files(fixture_repo, tmp_path):
    # Arrange
    source = GitSource(url=f"file://{fixture_repo}", protocol="file", host="")
    # Act
    run_git_clone(source, tmp_path / "dest")
    # Assert
    assert not (tmp_path / "dest" / "link").is_symlink()


def test_clone_over_size_cap_is_refused(fixture_repo, tmp_path):
    # Arrange
    source = GitSource(url=f"file://{fixture_repo}", protocol="file", host="")
    # Act
    ok, _reason = run_git_clone(source, tmp_path / "dest", max_bytes=16)
    # Assert
    assert ok is False


def test_option_shaped_url_is_not_parsed_as_an_option(tmp_path):
    # Arrange
    marker = tmp_path / "PWNED"
    source = GitSource(url=f"--upload-pack=touch {marker}", protocol="file", host="")
    # Act
    run_git_clone(source, tmp_path / "dest", protocols=("file",))
    # Assert
    assert not marker.exists()


# --------------------------------------------------------------------------- #
# End to end: project creation must not copy another tenant's repository       #
# --------------------------------------------------------------------------- #
VICTIM = "importvictim"
ATTACKER = "importattacker"


@pytest.fixture
def hub_root(settings, tmp_path):
    settings.BASE_DIR = tmp_path / "host"
    settings.BASE_DIR.mkdir()
    return settings.BASE_DIR


@pytest.fixture
def victim_repo(hub_root, django_user_model):
    django_user_model.objects.create_user(
        VICTIM, f"{VICTIM}@example.invalid", "pw-victim-1"
    )
    repo = hub_root / "data" / "users" / VICTIM / "proj" / "secret-proj"
    repo.mkdir(parents=True)
    _git("init", "-q", str(repo))
    (repo / "SECRET.txt").write_text("victim data\n")
    _git("add", "-A", cwd=repo)
    _git("commit", "-q", "-m", "init", cwd=repo)
    return repo


@pytest.fixture
def attacker_client(client, django_user_model):
    user = django_user_model.objects.create_user(
        ATTACKER, f"{ATTACKER}@example.invalid", "pw-attacker-1"
    )
    client.force_login(user)
    return client


def _imported_files(hub_root):
    proj = hub_root / "data" / "users" / ATTACKER / "proj"
    return {p.name for p in proj.rglob("*")} if proj.exists() else set()


@pytest.mark.django_db
@pytest.mark.parametrize("init_type", ["git", "github"])
@pytest.mark.parametrize("form", ["path", "file-url"])
def test_project_import_does_not_copy_another_tenants_repo(
    attacker_client, victim_repo, hub_root, init_type, form
):
    # Arrange
    url = str(victim_repo) if form == "path" else f"file://{victim_repo}"
    attacker_client.post(
        "/new/",
        {"name": f"stolen-{init_type}-{form}", "init_type": init_type, "git_url": url},
        # Act
    )
    # Assert
    assert "SECRET.txt" not in _imported_files(hub_root)
