"""Exercise actual path policy without requiring Docker paths to exist."""

import runpy
from pathlib import Path

import pytest

SOURCE = (
    Path(__file__).resolve().parents[6]
    / "apps/workspace/console_app/views/terminal/_runtime_preflight.py"
)
POLICY = runpy.run_path(str(SOURCE))
validate = POLICY["validate_terminal_host_paths"]
ConfigurationError = POLICY["TerminalConfigurationError"]


@pytest.mark.parametrize(
    "bad",
    [
        "",
        "relative.sif",
        "/path/to/singularity/current-sandbox",
        "/path/to/data/users",
        "/",
        "/scratch/..",
    ],
)
def test_unconfigured_image_is_a_permanent_configuration_error(bad):
    with pytest.raises(ConfigurationError, match="compute image.*not configured"):
        validate(bad, "/srv/research/users")


def test_workspace_placeholder_is_rejected_separately():
    with pytest.raises(ConfigurationError, match="workspace storage.*not configured"):
        validate("/srv/images/qualified.sif", "/path/to/data/users")


def test_remote_compute_paths_do_not_need_local_existence():
    assert (
        validate("/remote/compute/images/qualified.sif", "/remote/compute/users")
        is None
    )
