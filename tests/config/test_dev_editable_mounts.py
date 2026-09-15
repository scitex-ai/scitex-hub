import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
INSTALLER = ROOT / "deployment/docker/docker_dev/install_ecosystem.sh"


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


def test_editable_install_is_verified_against_the_mounted_checkout() -> None:
    source = INSTALLER.read_text()

    assert "Editable project location:" in source
    assert 'if [ "$editable_location" = "$mount_path" ]' in source
    assert 'uv pip install -e "$install_spec"' in source
