"""Exercise image-only vocabulary materialization with the unchanged guard."""

import importlib.util
import os
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


def _module(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


MATERIALIZE = _module(
    "image_vocabulary", "scripts/deploy/materialize_image_vocabulary.py"
)
BOOT = _module("bootstrap_vocabulary", "scripts/deploy/verify_default_bootstrap.py")


def test_materialization_is_wired_before_image_ownership_and_admission():
    source = (ROOT / "deployment/docker/docker_prod/Dockerfile.prod").read_text()
    materialization = source.index(
        "RUN --network=none python -I -S scripts/deploy/materialize_image_vocabulary.py"
    )
    ownership = source.index("chown -R scitex:scitex /app/data /app/.scitex")
    admission = source.index("verify_default_bootstrap.py --constructor")
    assert materialization < ownership < admission


@pytest.fixture
def image_tree(tmp_path):
    source = tmp_path / "src/scitex_hub/_cli_audit_dict.yaml"
    source.parent.mkdir(parents=True)
    source.write_bytes(b"words:\n  - vocabulary-fixture\n")
    target = tmp_path / ".scitex/dev/cli-audit-dict.yaml"
    target.parent.mkdir(parents=True)
    target.symlink_to("../../src/scitex_hub/_cli_audit_dict.yaml")
    return tmp_path, source, target


def test_source_link_is_rejected_by_the_original_constructor(image_tree):
    root, _, _ = image_tree
    with pytest.raises(AssertionError):
        BOOT.constructor_metadata([root / ".scitex"], [], os.getuid(), os.getgid())


def test_materialized_default_passes_the_original_constructor(image_tree):
    root, source, target = image_tree
    before = source.read_bytes()
    MATERIALIZE.materialize(root)
    metadata = BOOT.constructor_metadata(
        [root / ".scitex"], [], os.getuid(), os.getgid()
    )
    assert (
        target.is_symlink(),
        target.read_bytes(),
        source.read_bytes(),
        metadata[str(target)]["mode"],
    ) == (False, before, before, 0o600)


def test_materialization_is_idempotent(image_tree):
    root, _, target = image_tree
    MATERIALIZE.materialize(root)
    inode = target.stat().st_ino
    MATERIALIZE.materialize(root)
    assert target.stat().st_ino == inode


def test_unexpected_link_is_refused_without_touching_its_target(image_tree):
    root, _, target = image_tree
    external = root / "external"
    external.write_bytes(b"preserve")
    target.unlink()
    target.symlink_to(external)
    with pytest.raises(ValueError):
        MATERIALIZE.materialize(root)
    assert target.is_symlink() and external.read_bytes() == b"preserve"


def test_existing_different_configuration_is_preserved(image_tree):
    root, _, target = image_tree
    target.unlink()
    target.write_bytes(b"preserve configuration")
    with pytest.raises(ValueError):
        MATERIALIZE.materialize(root)
    assert target.read_bytes() == b"preserve configuration"
