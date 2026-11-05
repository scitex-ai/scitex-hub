"""Application entrypoints must not perform global scheduler recovery.

Web and worker starts share these scripts. Their lifecycle must not cancel
other work or reset scheduler node state, even behind a web-role guard.
This configuration contract checks the actual shipped entrypoints; the old
cleanup block provides a negative control without contacting a scheduler.
"""

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
ENTRYPOINTS = (
    "deployment/docker/docker_dev/entrypoint.sh",
    "deployment/docker/common/scripts/entrypoint-dev.sh",
    "deployment/docker/common/scripts/entrypoint-prod.sh",
    "deployment/docker/docker_prod/entrypoint.sh",
)
OLD_CLEANUP = """
if command -v scancel &>/dev/null; then
    scancel --state=COMPLETING 2>/dev/null || true
    for node in $(sinfo -h -o"%N" 2>/dev/null); do
        scontrol update NodeName="$node" State=resume 2>/dev/null || true
    done
fi
"""


def _scheduler_mutations(script):
    """Find direct scheduler cancellation/update commands in startup source."""
    return re.findall(
        r"(?m)^[ \t]*(?:exec[ \t]+)?(?:/[^\s]+/)?"
        r"(scancel\b|scontrol[ \t]+update\b)",
        script,
    )


@pytest.mark.parametrize("entrypoint", ENTRYPOINTS)
def test_application_entrypoint_does_not_mutate_scheduler(entrypoint):
    # Arrange
    source = (ROOT / entrypoint).read_text(encoding="utf-8")
    # Act
    commands = _scheduler_mutations(source)
    # Assert
    assert commands == [], entrypoint


@pytest.mark.parametrize("web_guarded", [False, True])
def test_checker_rejects_the_old_cleanup_even_in_a_web_role(web_guarded):
    # Arrange
    source = OLD_CLEANUP
    if web_guarded:
        source = 'if [ "$IS_WEB_ROLE" = true ]; then\n' + source + "\nfi"
    # Act
    commands = _scheduler_mutations(source)
    # Assert
    assert commands == ["scancel", "scontrol update"]
