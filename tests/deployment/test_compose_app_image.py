"""Candidate identity and Python-mode policy use the real canonical Bash resolver."""

import os
from pathlib import Path
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[2]
RESOLVER = ROOT / "scripts/deploy/compose_env.sh"


def _resolve(environment, image=None, *, provided=False, ambient="hostile"):
    child = dict(os.environ)
    child.pop("BASH_ENV", None)
    child.pop("SCITEX_HUB_APP_IMAGE", None)
    child["SCITEX_HUB_RESOLVED_PYTHON_MODE"] = ambient
    if provided:
        child["SCITEX_HUB_APP_IMAGE"] = image
    script = 'source "$1"; resolve_compose_env "$2" "$3" || exit; printf "%s\\n" "$SCITEX_HUB_RESOLVED_PYTHON_MODE" "${SCITEX_HUB_APP_IMAGE-unset}" "$COMPOSE_CMD"'
    return subprocess.run(["bash", "--noprofile", "--norc", "-c", script,
                           "owned-image-policy", str(RESOLVER), environment, str(ROOT)],
                          env=child, capture_output=True, text=True, timeout=10)


@pytest.mark.parametrize("environment,expected", [("prod", "image-only"), ("staging", "editable"), ("dev", "editable")])
def test_unset_image_preserves_the_declared_environment_default(environment, expected):
    # Arrange / Act
    result = _resolve(environment)
    # Assert
    assert result.returncode == 0 and result.stdout.splitlines()[:2] == [expected, "unset"]


@pytest.mark.parametrize("environment", ["prod", "staging"])
@pytest.mark.parametrize("image", ["owned-candidate:v0.22.0-alpha-proof", "sha256:" + "a" * 64,
                                   "registry.example:5000/owned/candidate@sha256:" + "b" * 64])
def test_candidate_forces_image_only_for_both_supported_environments(environment, image):
    # Arrange / Act
    result = _resolve(environment, image, provided=True, ambient="editable")
    # Assert
    assert result.returncode == 0 and result.stdout.splitlines()[:2] == ["image-only", image]


@pytest.mark.parametrize("image", ["", " ", "https://owned-secret.invalid/image", "user:owned-secret-marker@registry/image",
                                   "candidate?owned-secret-marker", "$(owned-secret-marker)", "sha256:short",
                                   "candidate@sha256:short", "candidate@owned-secret-marker@sha256:" + "a" * 64, "candidate\nowned-secret-marker", "x" * 1025])
def test_unsafe_override_is_refused_without_echoing_its_value(image):
    # Arrange / Act
    result = _resolve("prod", image, provided=True)
    # Assert
    assert result.returncode == 2 and not result.stdout and "owned-secret" not in result.stderr and "value withheld" in result.stderr


def test_direct_bind_development_does_not_silently_ignore_a_candidate_image():
    # Arrange / Act
    result = _resolve("dev", "owned-candidate:proof", provided=True)
    # Assert
    assert result.returncode == 2 and "supported only for prod/staging" in result.stderr
