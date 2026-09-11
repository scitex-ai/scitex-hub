"""The shell-only SMTP credential reaches every dev email process.

The important contract is Compose's *effective* configuration. Merely parsing
the source YAML would keep passing if interpolation semantics changed or a later
Compose layer replaced an environment entry.
"""

from __future__ import annotations

import os
import pathlib
import re
import shutil
import subprocess

import pytest
import yaml

REPO = pathlib.Path(__file__).resolve().parents[2]
DEV_COMPOSE = REPO / "deployment/docker/docker_dev/docker-compose.yml"
CREDENTIAL = "SCITEX_HUB_EMAIL_HOST_PASSWORD"
REQUIRED = {"django", "celery_worker", "celery_beat"}
SENTINEL = "compose-test-smtp-password-not-a-secret"


def _compose_environment(
    tmp_path: pathlib.Path, value: str | None
) -> subprocess.CompletedProcess:
    """Render in an isolated project containing no developer env files."""
    compose = tmp_path / "docker-compose.yml"
    shutil.copyfile(DEV_COMPOSE, compose)
    (tmp_path / ".env").write_text("", encoding="utf-8")

    environment = {
        "HOME": str(tmp_path),
        "PATH": os.environ["PATH"],
        "XDG_CONFIG_HOME": str(tmp_path / "config"),
    }
    if value is not None:
        environment[CREDENTIAL] = value

    return subprocess.run(
        ["docker", "compose", "-f", str(compose), "config"],
        cwd=tmp_path,
        env=environment,
        text=True,
        capture_output=True,
        check=False,
    )


@pytest.fixture(scope="module")
def effective_services(tmp_path_factory: pytest.TempPathFactory) -> dict:
    result = _compose_environment(tmp_path_factory.mktemp("compose-email"), SENTINEL)
    assert result.returncode == 0, result.stderr
    return yaml.safe_load(result.stdout)["services"]


@pytest.mark.parametrize("name", sorted(REQUIRED))
def test_effective_service_receives_shell_credential(name, effective_services):
    """Assert the resolved value, not just the raw ``${...}`` declaration."""
    assert effective_services[name]["environment"][CREDENTIAL] == SENTINEL


def test_every_effective_celery_service_receives_shell_credential(
    effective_services,
):
    celery_services = sorted(
        name for name in effective_services if name.startswith("celery")
    )
    assert celery_services, "no celery services found — the compose layout changed"
    missing = [
        name
        for name in celery_services
        if effective_services[name].get("environment", {}).get(CREDENTIAL) != SENTINEL
    ]
    assert not missing, f"celery services missing the effective credential: {missing}"


@pytest.mark.parametrize("value", [None, ""], ids=["unset", "empty"])
def test_compose_refuses_an_unusable_shell_credential(tmp_path, value):
    result = _compose_environment(tmp_path, value)
    assert result.returncode != 0, "compose accepted a missing SMTP credential"
    assert CREDENTIAL in result.stderr
    assert SENTINEL not in result.stderr


def _is_deployment_input(path: pathlib.Path) -> bool:
    """Recognize Compose YAML and every conventional dotenv filename."""
    name = path.name
    return (
        path.suffix in {".yml", ".yaml"}
        or name == ".env"
        or name.startswith(".env.")
        or name.endswith(".env")
    )


def _tracked_deployment_inputs() -> list[pathlib.Path]:
    """Return versioned inputs only; ignored local secret files are never read."""
    result = subprocess.run(
        ["git", "ls-files", "-z", "--", "deployment/docker"],
        cwd=REPO,
        capture_output=True,
        check=True,
    )
    paths = [REPO / os.fsdecode(raw) for raw in result.stdout.split(b"\0") if raw]
    return sorted(path for path in paths if _is_deployment_input(path))


def _is_substitution(value: str) -> bool:
    return value.startswith("${") and value.endswith("}")


def test_no_tracked_deployment_input_commits_a_credential_value():
    """Scan tracked inputs without ever opening ignored, potentially real secrets."""
    inputs = _tracked_deployment_inputs()
    expected = REPO / "deployment/docker/envs/.env.example"
    assert expected in inputs, "dotenv discovery lost its checked-in deletion sentinel"
    expected_link = REPO / "deployment/docker/docker_dev/.env"
    assert expected_link in inputs, "exact .env discovery lost its tracked sentinel"

    offenders: list[str] = []
    pattern = re.compile(rf"{CREDENTIAL}=(.+)$", re.MULTILINE)
    for path in inputs:
        # The tracked docker_dev/.env is a deliberately dangling symlink in a
        # clean clone. Never follow it into an operator-created ignored env file.
        if path.is_symlink():
            continue
        assert path.is_file(), f"tracked deployment input was deleted: {path}"
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            match = pattern.search(line.strip())
            if not match:
                continue
            value = match.group(1).strip()
            if _is_substitution(value):
                continue
            if value.upper().startswith(
                ("CHANGE_ME", "YOUR_", "PLACEHOLDER", "EXAMPLE")
            ):
                continue
            offenders.append(f"{path.relative_to(REPO)}: {CREDENTIAL}=<redacted>")

    assert not offenders, f"tracked SMTP credential values found: {offenders}"


@pytest.mark.parametrize(
    "name",
    [".env", ".env.dev", ".env.production.local", "service.env", "compose.yaml"],
)
def test_deployment_input_discovery_covers_real_dotenv_names(name):
    assert _is_deployment_input(pathlib.Path(name))


def test_discovery_control_is_sensitive_to_file_deletion(tmp_path):
    """CONTROL: deleting a dotenv candidate changes filesystem discovery."""
    candidates = [tmp_path / ".env", tmp_path / ".env.dev", tmp_path / "service.env"]
    for path in candidates:
        path.touch()

    def discover() -> list[str]:
        return sorted(
            path.name for path in tmp_path.iterdir() if _is_deployment_input(path)
        )

    assert discover() == [".env", ".env.dev", "service.env"]
    (tmp_path / ".env.dev").unlink()
    assert discover() == [".env", "service.env"]


def test_literal_detector_control():
    pattern = re.compile(rf"{CREDENTIAL}=(.+)$", re.MULTILINE)
    sample = f"{CREDENTIAL}=synthetic-not-a-real-secret"  # pragma: allowlist secret
    match = pattern.search(sample)
    assert match is not None
    assert not _is_substitution(match.group(1).strip())
