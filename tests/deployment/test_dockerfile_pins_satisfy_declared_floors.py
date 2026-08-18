#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""A version pinned in the Dockerfile must satisfy what pyproject declares.

WHAT THIS LOCKS, and what it cost to learn.

On 2026-08-18 scitex.ai went down twice. hub's pyproject declared
``scitex-writer>=2.42.0``; the production image shipped ``2.26.1``; Django died
at startup on a module-scope ``import scitex_writer.workspace_layout``, which
does not exist before 2.42.0.

Both facts were true at the same time, and neither was wrong on its own:

    Dockerfile.prod line 462   uv pip install --system --no-cache ".[all]"
                               ^ installs hub's declared floors, correctly
    Dockerfile.prod line 531   "scitex-writer==2.42.0"   (was ==2.26.1)
                               ^ runs 69 lines LATER and wins

The C0 pin exists for a good reason -- it caches the dependency tree, and
scitex-writer is deliberately excluded from the C1 blanket upgrade because the
2.18.0-2.26.0 PyPI wheels were broken (2026-07-08 visitor-pool outage). The
Dockerfile even says how to keep it honest: "bump the C0 pin deliberately per
release". Nobody did, for 2.42.0. Nothing noticed, because nothing was looking.

So this is not a test that the pin has a particular value -- that would be a
fourth place to update and a fourth place to forget. It asserts the RELATIONSHIP
the two files must always hold: whatever the Dockerfile pins must satisfy what
pyproject asks for. The pin stays free to move; it just cannot contradict the
declaration.

WHY A RELATIONSHIP AND NOT A LIST OF PACKAGES. scitex-writer is the one that bit
us, and a guard naming scitex-writer would pass forever while the next sibling
drifts. The exception set here is bounded and mechanical: packages that appear
in BOTH files are compared, and packages appearing in only one are ignored --
the Dockerfile legitimately pins things hub does not declare (build tooling),
and hub legitimately declares things the Dockerfile never pins. A property whose
exceptions cannot be enumerated is worse than an enumeration, because it fires
on legitimate cases and gets switched off.
"""

import pathlib
import re

import pytest
from packaging.requirements import Requirement
from packaging.version import Version

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
DOCKERFILE = REPO_ROOT / "deployment/docker/docker_prod/Dockerfile.prod"
PYPROJECT = REPO_ROOT / "pyproject.toml"

#: ``"package==1.2.3"`` as it appears inside a RUN uv pip install continuation.
_PINNED = re.compile(r'"([A-Za-z0-9_.-]+)==([0-9][^"]*)"')

#: A dependency line inside pyproject's ``dependencies = [...]`` array.
_DECLARED = re.compile(r'^\s*"([A-Za-z0-9_.-][^"]*)",?\s*$')


def _dockerfile_pins():
    """Every ``pkg==version`` the production Dockerfile installs explicitly."""
    return {
        name.lower().replace("_", "-"): version
        for name, version in _PINNED.findall(DOCKERFILE.read_text())
    }


def _declared_requirements():
    """hub's own ``[project] dependencies``, as parsed Requirements.

    Read from the ``dependencies = [`` array only. Comments are skipped, which
    matters here because this file's own rationale quotes version strings.
    """
    lines = PYPROJECT.read_text().splitlines()
    start = next(i for i, ln in enumerate(lines) if ln.strip() == "dependencies = [")
    # Scan to the line that is exactly "]". Using text.index("]") instead stops
    # at the first bracket inside a COMMENT -- this section's prose mentions
    # "[all]" and "[django]" -- which silently truncates the array to nothing
    # and makes the whole guard pass on an empty comparison. Caught by the
    # overlap control below, which is why that control exists.
    end = next(i for i, ln in enumerate(lines[start + 1 :], start + 1) if ln.strip() == "]")
    out = {}
    for line in lines[start + 1 : end]:
        stripped = line.strip()
        if stripped.startswith("#"):
            continue
        match = _DECLARED.match(line)
        if not match:
            continue
        try:
            req = Requirement(match.group(1))
        except Exception:
            continue
        out[req.name.lower().replace("_", "-")] = req
    return out


def _conflicts():
    """Packages both files mention, where the pin violates the declaration."""
    pins = _dockerfile_pins()
    declared = _declared_requirements()
    bad = []
    for name, req in declared.items():
        if name not in pins:
            continue
        pinned = pins[name]
        if not req.specifier.contains(Version(pinned), prereleases=True):
            bad.append(f"{name}: Dockerfile pins =={pinned}, pyproject wants {req.specifier}")
    return bad


def test_the_dockerfile_exists_and_is_readable():
    """Control. Without it, a moved path makes every check below vacuously green."""
    # Arrange
    path = DOCKERFILE

    # Act
    exists = path.is_file()

    # Assert
    assert exists, f"{path} is missing; the pin guard below cannot see anything"


def test_the_pin_scanner_actually_finds_pins():
    """Control on the SCANNER, not the subject.

    A regex that matches nothing reports zero conflicts and looks like success.
    This is the same silent-clean failure mode as grepping rendered output for a
    string the renderer mutated: absence is indistinguishable from correctness
    unless something proves the reader works.
    """
    # Arrange
    pins = _dockerfile_pins()

    # Act
    found_any = len(pins) > 0

    # Assert
    assert found_any, "the pin regex matched nothing; a zero-conflict result would be meaningless"


def test_the_declaration_parser_actually_finds_dependencies():
    """The matching control for the other half of the comparison."""
    # Arrange
    declared = _declared_requirements()

    # Act
    found_any = len(declared) > 0

    # Assert
    assert found_any, "parsed no dependencies from pyproject; the comparison would be vacuous"


def test_the_two_files_overlap_on_at_least_one_package():
    """If nothing overlaps, the guard is green by construction and guards nothing."""
    # Arrange
    overlap = set(_dockerfile_pins()) & set(_declared_requirements())

    # Act
    overlaps = len(overlap) > 0

    # Assert
    assert overlaps, (
        "no package is both pinned in the Dockerfile and declared in pyproject. "
        "Either the parsers broke or the build stopped pinning siblings — either "
        "way this guard is no longer checking anything."
    )


def test_no_dockerfile_pin_violates_a_declared_requirement():
    """The defect itself. This FAILS on the pre-fix tree, which is the point."""
    # Arrange
    conflicts = _conflicts()

    # Act
    report = "\n  ".join(conflicts)

    # Assert
    assert not conflicts, (
        "The production image would install versions hub's own pyproject forbids:\n  "
        + report
        + "\n\nThis took scitex.ai down twice on 2026-08-18. The C0 pin block in "
        "Dockerfile.prod runs AFTER `uv pip install \".[all]\"` and overrides it, so a "
        "stale pin silently wins over the declared floor. Bump the C0 pin to a version "
        "that satisfies the declaration — the Dockerfile's own comment says to bump it "
        "deliberately per release."
    )


@pytest.mark.parametrize("module", ["scitex_writer.workspace_layout"])
def test_module_scope_imports_are_named_in_the_build_smoke_test(module):
    """Hub imports these at MODULE SCOPE, so a missing one is an outage, not a bug.

    The build already smoke-tests ``import scitex_writer.writer``. That passed on
    2.26.1 while hub needed ``workspace_layout``, so the gate could not fail on
    the defect that was actually present. Anything hub imports at module scope
    belongs in that smoke test.
    """
    # Arrange
    dockerfile = DOCKERFILE.read_text()

    # Act
    smoke_tested = module in dockerfile

    # Assert
    assert smoke_tested, (
        f"hub imports {module} at module scope, but the build never imports it. "
        "A wheel missing it fails at Django startup in production instead of "
        "failing the build."
    )
