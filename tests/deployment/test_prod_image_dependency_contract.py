#!/usr/bin/env python3
"""Production services must preserve the dependency graph baked into the image."""

import importlib.util
import json
import os
import sys
import sysconfig
from pathlib import Path

import yaml
from packaging.requirements import Requirement

REPO = Path(__file__).resolve().parents[2]
COMPOSE = REPO / "deployment/docker/docker_prod/docker-compose.yml"
INSTALLER = REPO / "scripts/apps/install_apps.sh"
DOCKERFILE = REPO / "deployment/docker/docker_prod/Dockerfile.prod"
ROOT_INIT = REPO / "deployment/docker/common/scripts/root-init.sh"
IMAGE_RUNTIME = REPO / "deployment/docker/common/scripts/image-runtime.sh"
VERIFIER = REPO / "scripts/deploy/verify_image_dependency_contract.py"
IMAGE_SERVICES = ("django", "celery_worker", "celery_worker_vis", "celery_beat")
WORKER_SERVICES = ("celery_worker", "celery_worker_vis", "celery_beat")


def _verifier_module():
    spec = importlib.util.spec_from_file_location("image_dependency_verifier", VERIFIER)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _compose():
    return yaml.safe_load(COMPOSE.read_text())


def _environment(service):
    values = _compose()["services"][service].get("environment", [])
    return dict(item.split("=", 1) for item in values)


def test_every_hub_python_service_forbids_runtime_editable_overrides():
    assert {
        service: _environment(service).get("SCITEX_APPS_PYTHON_MODE")
        for service in IMAGE_SERVICES
    } == dict.fromkeys(IMAGE_SERVICES, "image-only")


def test_image_only_services_do_not_overlay_verified_site_packages():
    overlays = {}
    for service in IMAGE_SERVICES:
        volumes = _compose()["services"][service].get("volumes", [])
        targets = [
            volume.split(":", 2)[1]
            for volume in volumes
            if isinstance(volume, str) and ":" in volume
        ]
        overlays[service] = [
            target
            for target in targets
            if target.startswith("/usr/local/lib/python3.11/site-packages/")
        ]

    assert overlays == {service: [] for service in IMAGE_SERVICES}


def test_image_only_mode_skips_editable_installs():
    text = INSTALLER.read_text()
    assert 'SCITEX_APPS_PYTHON_MODE' in text
    assert '"$PYTHON_MODE" == "image-only"' in text


def test_actual_runtime_image_runs_relationship_verifier_after_all_installs():
    text = DOCKERFILE.read_text()
    verifier_run = "RUN python /opt/scitex-image-contract/scripts/deploy/verify_image_dependency_contract.py"
    assert verifier_run in text
    assert text.index(verifier_run) > text.rindex('"crossref-local"')


def test_verifier_exists_and_cards_floor_is_release_target():
    assert VERIFIER.is_file()
    assert '"scitex-cards>=0.53.1"' in (REPO / "pyproject.toml").read_text()


def test_verifier_applies_requirements_for_activated_distribution_extras():
    verifier = _verifier_module()
    requirement = Requirement('scitex-scholar>=1.10; extra == "all"')

    assert verifier.requirement_applies(requirement, {"all"})
    assert not verifier.requirement_applies(requirement, set())


def test_final_scitex_upgrade_is_bare_and_declares_no_active_extra():
    dockerfile = DOCKERFILE.read_text()
    contract = json.loads((REPO / "scripts/deploy/preflight_contract.json").read_text())

    assert 'uv pip install --system --upgrade "scitex>=2.30.1"' in dockerfile
    assert "active_distribution_extras" not in contract


def test_verifier_does_not_apply_negative_marker_for_active_extra():
    verifier = _verifier_module()
    requirement = Requirement('demo>=1; extra != "all"')

    assert not verifier.requirement_applies(requirement, {"all"})
    assert verifier.requirement_applies(requirement, set())


def test_immutable_tree_rejects_application_writable_entries(tmp_path):
    verifier = _verifier_module()
    package = tmp_path / "package.py"
    package.write_text("pass\n")
    package.chmod(0o664)

    errors = verifier.immutable_tree_errors(tmp_path, required_uid=os.getuid())

    assert errors == [f"{package}: group/other-writable mode 0o664"]


def test_immutable_tree_rejects_symlink_to_writable_external_target(tmp_path):
    verifier = _verifier_module()
    verified = tmp_path / "verified"
    verified.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    outside.chmod(0o777)
    target = outside / "tool"
    target.write_text("#!/bin/sh\n")
    (verified / "tool").symlink_to(target)

    errors = verifier.immutable_tree_errors(verified, required_uid=os.getuid())

    assert any(str(outside) in error and "group/other-writable" in error for error in errors)


def test_immutable_tree_checks_descendants_of_external_directory_symlink(tmp_path):
    verifier = _verifier_module()
    verified = tmp_path / "verified"
    verified.mkdir()
    external = tmp_path / "external"
    external.mkdir()
    module = external / "package" / "unsafe.py"
    module.parent.mkdir()
    module.write_text("pass\n")
    module.chmod(0o664)
    (verified / "external-package").symlink_to(external, target_is_directory=True)

    errors = verifier.immutable_tree_errors(verified, required_uid=os.getuid())

    assert f"{module}: group/other-writable mode 0o664" in errors


def test_runtime_immutability_checks_python_packages_and_console_scripts(monkeypatch):
    verifier = _verifier_module()
    checked = []
    monkeypatch.setattr(
        verifier,
        "immutable_tree_errors",
        lambda root, required_uid=0: checked.append((root, required_uid)) or [],
    )

    assert verifier.runtime_immutability_errors() == []
    assert checked == [
        (Path(sysconfig.get_paths()["purelib"]), 0),
        (Path(sys.executable).resolve().parent, 0),
    ]


def test_image_only_runtime_does_not_grant_package_write_access_to_scitex():
    dockerfile = DOCKERFILE.read_text()
    root_init = ROOT_INIT.read_text()
    verifier = "/opt/scitex-image-contract/scripts/deploy/verify_image_dependency_contract.py"

    assert "COPY --from=python-builder --chown=1000:1000 /usr/local/lib/python3.11/site-packages" not in dockerfile
    assert "find /usr/local/lib/python3.11/site-packages ! -user scitex" not in dockerfile
    assert 'if [ "${SCITEX_APPS_PYTHON_MODE:-editable}" = "image-only" ]; then' in root_init
    assert f"COPY scripts/deploy/verify_image_dependency_contract.py {verifier}" in dockerfile
    assert dockerfile.index(f"COPY scripts/deploy/verify_image_dependency_contract.py {verifier}") > dockerfile.index(
        "COPY --chown=scitex:scitex . ."
    )
    assert f"gosu scitex python {verifier}" in root_init
    assert "python scripts/deploy/verify_image_dependency_contract.py" not in root_init


def test_image_only_workers_verify_then_drop_privileges_before_entrypoint():
    compose = _compose()
    assert {
        service: compose["services"][service]["entrypoint"]
        for service in WORKER_SERVICES
    } == {
        service: ["/usr/bin/tini", "--", "/image-runtime.sh", "/entrypoint.sh"]
        for service in WORKER_SERVICES
    }

    launcher = IMAGE_RUNTIME.read_text()
    verifier = "/opt/scitex-image-contract/scripts/deploy/verify_image_dependency_contract.py"
    assert f"gosu scitex python {verifier}" in launcher
    assert 'exec gosu scitex "$@"' in launcher
