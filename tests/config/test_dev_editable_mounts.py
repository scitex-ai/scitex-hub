import subprocess
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
INSTALLER = ROOT / "deployment/docker/docker_dev/install_ecosystem.sh"
ENTRYPOINT = ROOT / "deployment/docker/docker_dev/entrypoint.sh"
COMPOSE = ROOT / "deployment/docker/docker_dev/docker-compose.yml"
SAC_MOUNT = "/scitex-agent-container"


def test_installer_is_valid_shell() -> None:
    result = subprocess.run(
        ["bash", "-n", str(INSTALLER)],
        check=False,
        capture_output=True,
        text=True,
    )

    assert (result.returncode, result.stderr) == (0, "")


def test_migration_sentinel_does_not_skip_editable_mount_verification() -> None:
    source = INSTALLER.read_text()
    function = source.split("install_ecosystem_packages() {", 1)[1].split(
        "\n}", 1
    )[0]

    assert "MIGRATION_SENTINEL" not in function
    assert 'try_editable_install "/figrecipe" "figrecipe" "[all]"' in function
    assert (
        'try_editable_install "/scitex-agent-container" '
        '"scitex-agent-container" "[gui]"'
    ) in function


def test_editable_install_is_verified_against_the_mounted_checkout() -> None:
    source = INSTALLER.read_text()

    assert "Editable project location:" in source
    assert 'if [ "$editable_location" = "$mount_path" ]' in source
    assert 'uv pip install -e "$install_spec"' in source


def test_only_django_mounts_the_optional_sac_source() -> None:
    services = yaml.safe_load(COMPOSE.read_text(encoding="utf-8"))["services"]
    mounted_by = {
        name
        for name, service in services.items()
        for volume in service.get("volumes", [])
        if isinstance(volume, str)
        and f":{SAC_MOUNT}:" in volume
    }

    assert mounted_by == {"django"}


def test_django_preflight_proves_sac_import_and_exact_route() -> None:
    installer = INSTALLER.read_text(encoding="utf-8")
    entrypoint = ENTRYPOINT.read_text(encoding="utf-8")
    preflight = installer.split("verify_optional_sac_dashboard() {", 1)[1]

    assert '[ ! -f "/scitex-agent-container/pyproject.toml" ]' in preflight
    assert "import scitex_agent_container._django" in preflight
    assert 'resolve("/apps/agents/")' in preflight
    assert 'match.view_name != "scitex_agent_container:index"' in preflight
    django_branch = entrypoint.split(
        'if [ "$IS_DJANGO_CONTAINER" = true ]; then', 1
    )[1].split("else", 1)[0]
    assert "verify_optional_sac_dashboard" in django_branch
