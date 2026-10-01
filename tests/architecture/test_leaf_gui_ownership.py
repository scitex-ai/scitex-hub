"""Freeze legacy GUI behavior in Hub while leaf migrations preserve parity."""

import hashlib
import json
import subprocess
from pathlib import Path


def test_domain_gui_changes_belong_in_leaf_packages():
    root = Path(__file__).resolve().parents[2]
    baseline = json.loads(Path(__file__).with_name("leaf_gui_legacy_baseline.json").read_text())
    paths = subprocess.check_output(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "--", *baseline["legacy_roots"]],
        cwd=root, text=True,
    ).splitlines()
    violations = []
    for relative in paths:
        path = root / relative
        if not path.is_file() or "migrations" in path.parts:
            continue
        if path.suffix not in baseline["extensions"]:
            continue
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if baseline["files"].get(relative) != digest:
            violations.append(relative)
    assert not violations, (
        "Move application behavior/UI changes to the owning leaf's _django package. "
        "Preserve and test legacy parity before cutover. Changed/new Hub domain files: "
        + ", ".join(violations)
    )


def test_clew_domain_is_owned_by_its_leaf():
    root = Path(__file__).resolve().parents[2]
    assert not (root / "apps/workspace/clew_app").exists()
    provider = (root / "apps/infra/project_app/services/project_store.py").read_text()
    assert "scitex_clew" not in provider
    assert "SCITEX_CLEW" not in provider
