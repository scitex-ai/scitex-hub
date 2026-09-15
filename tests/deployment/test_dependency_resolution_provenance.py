#!/usr/bin/env python3
"""Static contract for deterministic dependency-resolution cache refreshes."""

from __future__ import annotations

import hashlib
import os
import subprocess
from pathlib import Path

import pytest
import yaml

REPO = Path(__file__).resolve().parents[2]
NONCE_FILE = REPO / "deployment/docker/dependency-resolution.nonce"
RESOLVER = REPO / "scripts/deploy/resolve_dependency_resolution.sh"
REBUILD = REPO / "scripts/deploy/rebuild.sh"
VERIFIER = REPO / "scripts/deploy/verify_image_dependency_contract.py"

DOCKERFILES = (
    REPO / "deployment/docker/docker_prod/Dockerfile.prod",
    REPO / "deployment/docker/Dockerfile.prod",
    REPO / "deployment/docker/docker_dev/Dockerfile",
    REPO / "deployment/docker/Dockerfile",
)
RELEASE_COMPOSE = (
    REPO / "deployment/docker/docker_prod/docker-compose.yml",
    REPO / "deployment/docker/docker-compose.prod.yml",
    REPO / "deployment/docker/docker-compose.staging.yml",
)
DEV_COMPOSE = (
    REPO / "deployment/docker/docker_dev/docker-compose.yml",
    REPO / "deployment/docker/docker-compose.override.yml",
)
ARG = "SCITEX_HUB_DEPENDENCY_RESOLUTION"
INSTALL = 'uv pip install --system'


def _logical_instructions(text: str) -> list[str]:
    logical: list[str] = []
    current = ""
    for raw in text.splitlines():
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            continue
        current += ("\n" if current else "") + stripped
        if not stripped.endswith("\\"):
            logical.append(current)
            current = ""
    return logical


def _instruction_cache_keys(text: str, value: str) -> list[str]:
    """Model Docker's ordered cache inputs for the provenance ARG's first use."""
    logical = _logical_instructions(text)
    parent = "root"
    keys = []
    used = False
    for instruction in logical:
        rendered = instruction
        if instruction.startswith(("RUN ", "ENV ", "LABEL ")) and f"${{{ARG}}}" in instruction:
            rendered = instruction.replace(f"${{{ARG}}}", value)
            used = True
        digest = hashlib.sha256(f"{parent}\0{rendered}".encode()).hexdigest()
        keys.append(digest)
        parent = digest
    assert used, f"{ARG} is never consumed"
    return keys


def _install_instruction_index(text: str) -> int:
    return next(
        index
        for index, line in enumerate(text.splitlines())
        if INSTALL in line and '".[all]"' in line
    )


@pytest.mark.parametrize("dockerfile", DOCKERFILES, ids=lambda path: str(path.relative_to(REPO)))
def test_changed_dependency_input_preserves_layers_before_local_install(dockerfile: Path):
    text = dockerfile.read_text()
    old = _instruction_cache_keys(text, "release-1")
    new = _instruction_cache_keys(text, "release-2")
    changed = [index for index, pair in enumerate(zip(old, new)) if pair[0] != pair[1]]

    logical_install = next(
        index
        for index, instruction in enumerate(_logical_instructions(text))
        if INSTALL in instruction and '".[all]"' in instruction
    )
    assert changed, "the dependency input must invalidate a layer"
    assert min(changed) >= logical_install, "heavy/base layers were invalidated"


@pytest.mark.parametrize("dockerfile", DOCKERFILES, ids=lambda path: str(path.relative_to(REPO)))
def test_dependency_input_is_consumed_by_local_dependency_install(dockerfile: Path):
    text = dockerfile.read_text()
    install_at = _install_instruction_index(text)
    before_install = "\n".join(text.splitlines()[: install_at + 1])
    assert f"ARG {ARG}" in before_install
    assert f"dependency resolution: ${{{ARG}}}" in before_install


def _all_build_args(compose: Path):
    services = yaml.safe_load(compose.read_text())["services"]
    return {
        name: service["build"].get("args", {})
        for name, service in services.items()
        if isinstance(service, dict) and isinstance(service.get("build"), dict)
        and "Dockerfile" in service["build"].get("dockerfile", "")
        and "django" in service.get("image", "")
    }


@pytest.mark.parametrize("compose", RELEASE_COMPOSE, ids=lambda path: str(path.relative_to(REPO)))
def test_release_compose_fails_closed_when_dependency_input_is_missing(compose: Path):
    builds = _all_build_args(compose)
    assert builds
    assert {name: args.get(ARG) for name, args in builds.items()} == {
        name: f"${{{ARG}:?set by protected rebuild}}" for name in builds
    }


@pytest.mark.parametrize("compose", DEV_COMPOSE, ids=lambda path: str(path.relative_to(REPO)))
def test_dev_compose_keeps_ordinary_source_builds_working(compose: Path):
    builds = _all_build_args(compose)
    assert builds
    assert {name: args.get(ARG) for name, args in builds.items()} == {
        name: f"${{{ARG}:-dev}}" for name in builds
    }


def test_protected_rebuild_passes_committed_nonce_explicitly():
    text = REBUILD.read_text()
    assert 'resolve_dependency_resolution.sh" "$ENV"' in text
    assert f"export {ARG}" in text
    assert NONCE_FILE.read_text().strip()


def test_release_nonce_resolver_fails_closed_without_input(tmp_path: Path):
    env = os.environ | {"SCITEX_HUB_DEPENDENCY_RESOLUTION_FILE": str(tmp_path / "missing")}
    result = subprocess.run(
        [str(RESOLVER), "prod"], env=env, text=True, capture_output=True, check=False
    )
    assert result.returncode != 0
    assert "dependency-resolution" in result.stderr


def test_dev_nonce_resolver_allows_ordinary_source_rebuild(tmp_path: Path):
    env = os.environ | {"SCITEX_HUB_DEPENDENCY_RESOLUTION_FILE": str(tmp_path / "missing")}
    result = subprocess.run(
        [str(RESOLVER), "dev"], env=env, text=True, capture_output=True, check=False
    )
    assert result.returncode == 0
    assert result.stdout.strip() == "dev"


def test_final_image_verifier_reports_and_validates_provenance():
    text = VERIFIER.read_text()
    assert "dependency_resolution_provenance" in text
    assert "Dependency resolution provenance:" in text
