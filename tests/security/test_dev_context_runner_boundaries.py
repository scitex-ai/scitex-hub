"""Execute the real context boundary with owned files and inert runtimes."""

import importlib.util
import json
import logging
import os
import stat
import subprocess
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[2]
SERVICES = ROOT / "apps/workspace/apps_app/services"
SCRIPT = ROOT / "apps/workspace/apps_app/scripts/run_dev_context.py"
CANARY = "owned-canary-not-a-real-credential"


def load_source(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize(
    "image", ["--help", "relative.sif", "docker://owned/image", "/owned\n--help"]
)
def test_native_image_cannot_be_an_option_uri_or_relative_path(image, tmp_path):
    helper = load_source(
        "owned_native_image",
        ROOT / "apps/workspace/console_app/services/apptainer_runner.py",
    )
    with pytest.raises(ValueError, match="absolute native path"):
        helper.build_apptainer_exec_cmd(
            ["python", "owned.py"], tmp_path, container_path=image
        )


def test_native_image_separator_preserves_absolute_sif_and_sandbox_paths(tmp_path):
    helper = load_source(
        "owned_native_image",
        ROOT / "apps/workspace/console_app/services/apptainer_runner.py",
    )
    commands = [
        helper.build_apptainer_exec_cmd(
            ["python", "owned.py"], tmp_path, container_path=str(path)
        )
        for path in (tmp_path / "image with spaces.sif", tmp_path / "sandbox directory")
    ]
    assert [command[-4:] for command in commands] == [
        ["--", str(path), "python", "owned.py"]
        for path in (tmp_path / "image with spaces.sif", tmp_path / "sandbox directory")
    ]


@pytest.fixture
def runtime(tmp_path, monkeypatch):
    runner = load_source("owned_dev_runner", SERVICES / "dev_app_runner.py")
    helper = load_source(
        "owned_apptainer_builder",
        ROOT / "apps/workspace/console_app/services/apptainer_runner.py",
    )
    project = tmp_path / "project"
    project.mkdir()
    image = tmp_path / "approved image.sif"
    image.write_bytes(b"owned unused image fixture")
    state = SimpleNamespace(
        runner=runner,
        project=project,
        calls=[],
        paths=[],
        modes=[],
        contents=[],
        response=SimpleNamespace(
            returncode=0, stdout='{"success":true,"context":{"ok":true}}', stderr=""
        ),
        action=None,
        allocation=[],
        image=image,
    )
    loader = ModuleType("apps.workspace.apps_app.services.dev_app_loader")
    loader.resolve_dev_project_dir = lambda *_: project
    monkeypatch.setitem(sys.modules, loader.__name__, loader)
    allocations = ModuleType(
        "apps.workspace.console_app.services.terminal_broker.allocation"
    )
    allocations.Allocation = SimpleNamespace(
        find_existing_jobs=lambda _: state.allocation
    )
    monkeypatch.setitem(sys.modules, allocations.__name__, allocations)
    helper.get_container_for_user = lambda _: str(image)
    monkeypatch.setitem(
        sys.modules, "apps.workspace.console_app.services.apptainer_runner", helper
    )
    monkeypatch.setattr(runner, "_generate_api_token", lambda _: CANARY)

    def capture(argv, **kwargs):
        path = project / Path(argv[-1]).name
        state.calls.append({"argv": list(argv), **kwargs})
        state.paths.append(path)
        state.modes.append(stat.S_IMODE(path.stat().st_mode))
        state.contents.append(path.read_text())
        if state.action:
            return state.action(path)
        return state.response

    monkeypatch.setattr(
        runner,
        "subprocess",
        SimpleNamespace(run=capture, TimeoutExpired=subprocess.TimeoutExpired),
    )
    state.install = SimpleNamespace(
        source_owner="owner",
        source_repo="review",
        module_name="dev__owner__review",
        apptainer_container_path=str(image),
    )

    def invoke():
        return runner.run_dev_context(
            state.install, "owned-user", 7, "owned-project", {"q": "unchanged"}
        )

    state.invoke = invoke
    return state


def test_existing_symlink_cannot_overwrite_another_file(runtime, tmp_path):
    target = tmp_path / "outside-project.txt"
    target.write_text("preserve authored data")
    fixed = runtime.project / ".scitex_run_dev_context.py"
    fixed.symlink_to(target)
    runtime.invoke()
    assert (target.read_text(), fixed.is_symlink()) == ("preserve authored data", True)


def test_existing_fixed_helper_name_is_preserved(runtime):
    fixed = runtime.project / ".scitex_run_dev_context.py"
    fixed.write_text("authored file")
    runtime.invoke()
    assert fixed.read_text() == "authored file"


def test_overlapping_requests_use_distinct_owned_helpers(runtime):
    overlapping = []

    def nested(path):
        runtime.action = None
        runtime.invoke()
        overlapping.append(path.is_file())
        return runtime.response

    runtime.action = nested
    runtime.invoke()
    assert (
        len(set(runtime.paths)),
        overlapping,
        [p.exists() for p in runtime.paths],
    ) == (2, [True], [False, False])


def test_cleanup_does_not_unlink_a_replaced_file(runtime, tmp_path):
    replacement = tmp_path / "replacement"
    replacement.write_text("replacement must survive")

    def replace(path):
        os.replace(replacement, path)
        return runtime.response

    runtime.action = replace
    runtime.invoke()
    assert runtime.paths[0].read_text() == "replacement must survive"


@pytest.mark.parametrize("allocation", [[], [123]])
def test_metadata_and_credentials_use_stdin_not_argv_or_logs(
    runtime, caplog, allocation
):
    runtime.allocation = allocation
    runtime.install.module_name = "dev__literal,$(owned)"
    caplog.set_level(logging.DEBUG)
    runtime.invoke()
    call = runtime.calls[0]
    envelope = json.loads(call["input"])
    assert (
        CANARY not in str(call["argv"])
        and runtime.install.module_name not in str(call["argv"])
        and CANARY not in caplog.text
        and runtime.install.module_name not in caplog.text
        and envelope["app_env"]["SCITEX_API_TOKEN"] == CANARY
        and envelope["app_env"]["SCITEX_CURRENT_APP"] == runtime.install.module_name
        and envelope["payload"]["get_params"] == {"q": "unchanged"}
        and runtime.modes == [0o644]
        and CANARY not in runtime.contents[0]
    )


@pytest.mark.parametrize("returncode", [0, 1])
def test_untrusted_runtime_errors_are_not_logged(runtime, caplog, returncode):
    runtime.response = SimpleNamespace(
        returncode=returncode,
        stdout=json.dumps({"success": False, "error": CANARY}),
        stderr=CANARY,
    )
    caplog.set_level(logging.DEBUG)
    result = runtime.invoke()
    assert (result, CANARY in caplog.text, runtime.paths[0].exists()) == (
        {},
        False,
        False,
    )


def test_timeout_cleans_only_owned_helper(runtime):
    def timeout(path):
        raise subprocess.TimeoutExpired(["owned-runtime"], 1)

    runtime.action = timeout
    result = runtime.invoke()
    assert (result, runtime.paths[0].exists()) == ({}, False)


def test_runtime_exception_is_redacted_and_cleans_owned_helper(runtime, caplog):
    def fail(path):
        raise OSError(CANARY)

    runtime.action = fail
    caplog.set_level(logging.DEBUG)
    result = runtime.invoke()
    assert (result, CANARY in caplog.text, runtime.paths[0].exists()) == (
        {},
        False,
        False,
    )


def test_helper_write_error_cleans_exclusive_file(runtime, monkeypatch):
    def fail_mode(*args):
        raise OSError("owned staging failure")

    monkeypatch.setattr(runtime.runner.os, "fchmod", fail_mode)
    assert runtime.invoke() == {}
    assert runtime.calls == []
    assert list(runtime.project.iterdir()) == []


@pytest.mark.parametrize(
    "extra",
    [
        {},
        {"PATH": "/untrusted"},
        {"SCITEX_API_TOKEN": 1},
        {"SCITEX_API_TOKEN": "bad\0value"},
    ],
)
def test_sandbox_initializes_only_allowlisted_env_before_import(tmp_path, extra):
    project = tmp_path / "project"
    project.mkdir()
    marker = tmp_path / "imported"
    (project / "views.py").write_text(
        "import os\nfrom pathlib import Path\n"
        f"Path({str(marker)!r}).write_text('imported')\n"
        "AT_IMPORT = os.environ.get('SCITEX_API_TOKEN')\n"
        "def build_review_context(request, project):\n"
        " return {'token': AT_IMPORT, 'query': request.GET, 'project': project.slug}\n"
    )
    app_env = {
        "SCITEX_CURRENT_APP": "dev__owner__review",
        "SCITEX_API_TOKEN": CANARY,
        "SCITEX_API_URL": "http://owned.invalid",
    }
    app_env.update(extra)
    envelope = {
        "payload": {
            "function": "build_review_context",
            "username": "owned",
            "project_id": 7,
            "project_slug": "owned-project",
            "get_params": {"q": "original"},
        },
        "app_env": app_env,
    }
    harness = (
        "import importlib.util,sys\nfrom pathlib import Path\n"
        "s=importlib.util.spec_from_file_location('owned_runner',sys.argv[1]);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)\n"
        "real=Path;m.Path=lambda p: real(sys.argv[2]) if str(p)=='/workspace' else real(p)\n"
        "raise SystemExit(m.main())\n"
    )
    result = subprocess.run(
        [sys.executable, "-B", "-c", harness, str(SCRIPT), str(project)],
        input=json.dumps(envelope),
        text=True,
        capture_output=True,
        timeout=20,
    )
    response = json.loads(result.stdout)
    if extra:
        assert (result.returncode, response["success"], marker.exists()) == (
            1,
            False,
            False,
        )
    else:
        assert (result.returncode, response) == (
            0,
            {
                "success": True,
                "context": {
                    "token": CANARY,
                    "query": {"q": "original"},
                    "project": "owned-project",
                },
            },
        )
