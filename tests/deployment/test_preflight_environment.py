"""Resolved policy controls plus genuine isolated floor/import subprocesses.

The owned resolver fixture emits only a constructed Compose document. It is a
transport fixture, not a claim to run Docker or a production image. The probe
still executes real Python modules and distribution metadata in a separate
interpreter; its missing-floor/import negative controls remain meaningful.
"""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

DEPLOY = Path(__file__).resolve().parents[2] / "scripts/deploy"
sys.path.insert(0, str(DEPLOY))
import preflight_environment as environment
from preflight_targets import TargetUnreachable


def _document(mode="image-only"):
    return {"services": {name: {"image": "owned-image:reviewed", "environment": {
        "SCITEX_APPS_PYTHON_MODE": mode, "NEVER_EXPOSE": "owned-secret-marker",
    }, "volumes": [{"type": "volume", "source": "apps", "target": "/app/.apps"}]}
        for name in environment.PYTHON_ROLES}, "volumes": {"apps": {"name": "owned_apps_volume"}}}


def test_image_only_does_not_treat_frontend_clones_as_python_overlay():
    # Arrange
    context = environment.parse_context(_document())
    # Act
    target = environment.choose_target(context)
    # Assert
    assert target == ("image:owned-image:reviewed", None)


@pytest.mark.parametrize("read_only", [True, False])
@pytest.mark.parametrize("target", [
    "/usr/local/lib/python3.11/site-packages/scitex_container",
    "/usr/local/lib/python3.11/site-packages/scitex/scholar/citation_graph",
    "/usr/local", "/usr", "/", "/usr/local/bin/scitex-hub",
    "/opt/scitex-image-contract", "/opt/scitex-frontend/vite",
    "/opt/scitex-frontend-tools", "/root-init.sh", "/entrypoint.sh",
])
def test_image_only_refuses_runtime_shadowing_in_any_role(target, read_only):
    document = _document()
    document["services"]["celery_worker"]["volumes"].append({
        "type": "bind", "source": "/owned/checkout", "target": target,
        "read_only": read_only,
    })
    with pytest.raises(TargetUnreachable, match="qualified runtime code"):
        environment.parse_context(document)


def test_image_only_preserves_normal_data_and_static_mounts():
    document = _document()
    for target in ("/app/data/users", "/app/staticfiles", "/app/.scitex"):
        document["services"]["django"]["volumes"].append({
            "type": "bind", "source": "/owned/data", "target": target,
        })
    assert environment.parse_context(document).mode == "image-only"


def test_legacy_editable_uses_the_actual_declared_volume_name():
    # Arrange
    context = environment.parse_context(_document("editable"))
    # Act
    target = environment.choose_target(context)
    # Assert
    assert target == ("image:owned-image:reviewed", "owned_apps_volume")


@pytest.mark.parametrize("target", ["image:sha256:123", "container:owned", "local", "cmd:owned-runner"])
def test_explicit_target_identity_is_never_replaced(target):
    # Arrange
    context = environment.parse_context(_document())
    # Act
    result = environment.choose_target(context, target)
    # Assert
    assert result == (target, None)


def test_explicit_editable_target_does_not_silently_acquire_an_overlay():
    # Arrange
    context = environment.parse_context(_document("editable"))
    # Act
    result = environment.choose_target(context, "image:owned-candidate")
    # Assert
    assert result == ("image:owned-candidate", None)


@pytest.mark.parametrize("volume", ["", "arbitrary-overlay"])
def test_image_only_refuses_explicit_clone_overlay(volume):
    # Arrange
    context = environment.parse_context(_document())
    # Act / Assert
    with pytest.raises(TargetUnreachable):
        environment.choose_target(context, explicit_volume=volume)


def test_editable_volume_override_cannot_describe_a_different_deployment():
    # Arrange
    context = environment.parse_context(_document("editable"))
    # Act / Assert
    with pytest.raises(TargetUnreachable):
        environment.choose_target(context, explicit_volume="another-volume")


@pytest.mark.parametrize("mutation", ["missing-role", "missing-mode", "empty-mode", "unknown-mode", "mixed-mode", "mixed-image", "missing-image", "unresolved-env", "clone-path", "dev-image-only"])
def test_unsafe_or_missing_role_contract_is_refused(mutation):
    # Arrange
    document = _document()
    worker = document["services"]["celery_worker"]
    if mutation == "missing-role": del document["services"]["celery_beat"]
    elif mutation == "missing-mode": del worker["environment"]["SCITEX_APPS_PYTHON_MODE"]
    elif mutation == "empty-mode": worker["environment"]["SCITEX_APPS_PYTHON_MODE"] = ""
    elif mutation == "unknown-mode": worker["environment"]["SCITEX_APPS_PYTHON_MODE"] = "owned-secret-marker"
    elif mutation == "mixed-mode": worker["environment"]["SCITEX_APPS_PYTHON_MODE"] = "editable"
    elif mutation == "mixed-image": worker["image"] = "different-image:reviewed"
    elif mutation == "missing-image": del worker["image"]
    elif mutation == "unresolved-env": worker["environment"] = []
    elif mutation == "clone-path": worker["environment"]["PYTHONPATH"] = "/app/./.apps/owned/src:/app"
    elif mutation == "dev-image-only": worker["entrypoint"] = ["/app/deployment/docker/docker_dev/entrypoint.sh"]
    # Act / Assert
    with pytest.raises(TargetUnreachable):
        environment.parse_context(document)


@pytest.mark.parametrize("mutation", ["missing-mount", "mixed-mount", "unresolved-volume", "unsupported-bind"])
def test_editable_overlay_must_be_resolved_and_agreed(mutation):
    # Arrange
    document = _document("editable")
    worker = document["services"]["celery_worker"]
    if mutation == "missing-mount": worker["volumes"] = []
    elif mutation == "mixed-mount":
        worker["volumes"][0]["source"] = "other"
        document["volumes"]["other"] = {"name": "other_volume"}
    elif mutation == "unresolved-volume": document["volumes"]["apps"] = {}
    else: worker["volumes"][0] = {"type": "bind", "source": "relative/owned", "target": "/app/.apps"}
    # Act / Assert
    with pytest.raises(TargetUnreachable):
        environment.parse_context(document)


def test_summary_never_copies_the_resolved_secret_environment():
    # Arrange
    context = environment.parse_context(_document())
    # Act
    public = json.dumps(context.summary())
    # Assert
    assert "owned-secret-marker" not in public


def _source_fixture(root):
    spec = importlib.util.spec_from_file_location("owned_deploy_fixtures", Path(__file__).with_name("conftest.py"))
    fixtures = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(fixtures)
    repo, site, contract, runner = fixtures._build(root, ["demosib-writer>=2.42.0"],
        {"apps/demo/urls.py": "from demosib_writer.workspace_layout import compile_script\n"})
    return fixtures, repo, site, contract, runner


def _resolver(repo, document=None, malformed=False, failing=False):
    folder = repo / "scripts/deploy"
    folder.mkdir(parents=True)
    producer = folder / "owned-compose-result.py"
    if failing:
        body = "import sys;print('owned-secret-marker',file=sys.stderr);sys.exit(9)"
    elif malformed:
        body = "print('owned-secret-marker invalid JSON')"
    else:
        body = "import json,sys;assert sys.argv[1:]==['config','--format','json'];print(json.dumps(" + repr(document or _document()) + "))"
    producer.write_text(body)
    # Source a real owned resolver in Bash, exercising the same canonical SPI.
    (folder / "compose_env.sh").write_text(
        'resolve_compose_env() { DOCKER_DIR="$2"; COMPOSE_CMD="' + sys.executable + ' ' + str(producer) + '"; }\n')


def _drive_env(repo, contract, runner, extra=()):
    return subprocess.run([sys.executable, str(DEPLOY / "preflight_sibling_floors.py"),
        "--env", "prod", "--target", "cmd:/bin/sh " + str(runner), "--repo-root", str(repo),
        "--pyproject", str(repo / "pyproject.toml"), "--contract", str(contract), "--json", *extra],
        capture_output=True, text=True, timeout=30, env=dict(os.environ, SCITEX_APPS_PYTHON_MODE="editable"))


@pytest.mark.parametrize("version,expected", [("2.41.0", 1), ("2.42.0", 0)])
def test_image_only_still_checks_actual_floor_and_imports_in_child(tmp_path, version, expected):
    # Arrange
    fixtures, repo, site, contract, runner = _source_fixture(tmp_path)
    fixtures._install(site, "demosib-writer", version, {"demosib_writer/__init__.py": "", "demosib_writer/workspace_layout.py": "compile_script = None\n"})
    _resolver(repo)
    # Act
    result = _drive_env(repo, contract, runner)
    # Assert
    assert result.returncode == expected, result.stdout + result.stderr


def test_image_only_does_not_hide_a_real_missing_import(tmp_path):
    # Arrange
    fixtures, repo, site, contract, runner = _source_fixture(tmp_path)
    fixtures._install(site, "demosib-writer", "2.42.0", {"demosib_writer/__init__.py": ""})
    _resolver(repo)
    # Act
    result = _drive_env(repo, contract, runner)
    # Assert
    assert result.returncode == 1 and "IMPORT FAILS INSIDE THE TARGET" in result.stdout


@pytest.mark.parametrize("kind", ["failure", "invalid-json", "unknown-mode"])
def test_invalid_compose_resolution_fails_closed_without_secret_output(tmp_path, kind):
    # Arrange
    _fixtures, repo, _site, contract, runner = _source_fixture(tmp_path)
    document = _document()
    if kind == "unknown-mode": document["services"]["django"]["environment"]["SCITEX_APPS_PYTHON_MODE"] = "owned-secret-marker"
    _resolver(repo, document, malformed=kind == "invalid-json", failing=kind == "failure")
    # Act
    result = _drive_env(repo, contract, runner)
    # Assert
    assert result.returncode == 2 and "owned-secret-marker" not in result.stdout + result.stderr


def test_unresolved_configuration_never_runs_the_target(tmp_path):
    # Arrange
    _fixtures, repo, _site, contract, runner = _source_fixture(tmp_path)
    marker = tmp_path / "target-ran"
    runner.write_text("#!/bin/sh\n" + "touch " + str(marker) + "\nexit 99\n")
    _resolver(repo, malformed=True)
    # Act
    result = _drive_env(repo, contract, runner)
    # Assert
    assert result.returncode == 2 and not marker.exists()


def _wrapper_fixture(root):
    import shutil
    folder = root / "scripts/deploy"
    folder.mkdir(parents=True)
    for name in ["compose.sh", "compose_env.sh"]:
        shutil.copy2(DEPLOY / name, folder / name)
    (root / "deployment/docker/docker_prod").mkdir(parents=True)
    gate = folder / "preflight_sibling_floors.sh"
    gate.write_text('#!/bin/sh\nprintf "%s\\n" "$@" > "' + str(root / "gate-args") + '"\n')
    gate.chmod(0o755)
    binary = root / "bin"
    binary.mkdir()
    docker = binary / "docker"
    docker.write_text('#!/bin/sh\nprintf "%s\\n" "$@" > "' + str(root / "docker-args") + '"\n')
    docker.chmod(0o755)
    return folder / "compose.sh", dict(os.environ, PATH=str(binary) + os.pathsep + os.environ["PATH"])


@pytest.mark.parametrize("arguments", [["-f", "another.yml", "up", "-d"],
                                      ["--env-file", "other.env", "up"],
                                      ["--project-name=other", "up"]])
def test_wrapper_refuses_unmodelled_recreate_configuration(tmp_path, arguments):
    # Arrange
    script, child_env = _wrapper_fixture(tmp_path)
    # Act
    result = subprocess.run(["bash", str(script), "prod", *arguments], env=child_env,
                            capture_output=True, text=True, timeout=10)
    # Assert
    assert result.returncode == 2 and not (tmp_path / "docker-args").exists() and not (tmp_path / "gate-args").exists()


@pytest.mark.parametrize("arguments,gate", [(["up", "-d", "--force-recreate", "django"], True),
                                            (["build", "django"], False),
                                            (["logs", "-f", "django"], False)])
def test_wrapper_keeps_normal_up_build_and_readonly_commands(tmp_path, arguments, gate):
    # Arrange
    script, child_env = _wrapper_fixture(tmp_path)
    # Act
    result = subprocess.run(["bash", str(script), "prod", *arguments], env=child_env,
                            capture_output=True, text=True, timeout=10)
    # Assert
    assert result.returncode == 0 and (tmp_path / "docker-args").exists() and (tmp_path / "gate-args").exists() == gate
