"""Contract for the screenshot runner's writable terminal workspace."""

from pathlib import Path

import yaml

WORKFLOW = Path(".github/workflows/screenshots.yml")
USER_DATA_ROOT = "${{ runner.temp }}/scitex-users"


def _steps():
    workflow = yaml.safe_load(WORKFLOW.read_text())
    return {step["name"]: step for step in workflow["jobs"]["screenshots"]["steps"]}


def test_server_and_capture_share_runner_user_data_root():
    steps = _steps()

    for name in ("Migrate & start server", "Capture screenshots"):
        assert steps[name]["env"]["SCITEX_HUB_USER_DATA_ROOT"] == USER_DATA_ROOT


def test_user_data_root_is_created_before_server_starts():
    run = _steps()["Migrate & start server"]["run"]

    mkdir = 'mkdir -p "$SCITEX_HUB_USER_DATA_ROOT"'
    runserver = "python manage.py runserver"
    assert mkdir in run
    assert run.index(mkdir) < run.index(runserver)


def test_registered_screenshot_user_gets_a_real_writer_workspace():
    run = _steps()["Migrate & start server"]["run"]
    runserver = "python manage.py runserver"

    required = (
        "Project.objects.get_or_create",
        "create_project_directory",
        "ensure_workspace",
        "last_active_repository",
    )
    for token in required:
        assert token in run
        assert run.index(token) < run.index(runserver)

    assert "visitor" not in run.lower()
    assert "guest" not in run.lower()
