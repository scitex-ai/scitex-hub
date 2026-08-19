#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""The Dockerfile's pinned packages must be satisfiable TOGETHER.

WHAT THIS LOCKS, and it is the gap in its own sibling guard.

tests/deployment/test_dockerfile_pins_satisfy_declared_floors.py compares each
Dockerfile pin against hub's ``pyproject.toml``. Every pin passed it on
2026-08-19 and the production image still would not build:

    Because scitex-writer==2.42.0 depends on scitex-ui>=0.8.0
      and you require scitex-writer==2.42.0, we can conclude that you
      require scitex-ui>=0.8.0.
    And because you require scitex-ui==0.6.3, we can conclude that your
      requirements are unsatisfiable.

Both pins were individually correct. ``scitex-writer==2.42.0`` satisfied hub's
declared floor; ``scitex-ui==0.6.3`` violated nothing hub declares, because hub
does not declare scitex-ui at all -- it arrives transitively. The conflict lives
BETWEEN the pins, in a requirement neither file mentions.

So the sibling guard was not wrong; it was answering a different question. This
one asks: given the versions we pin, does any pinned package's own dependency
contradict another pin?

WHY IT READS INSTALLED METADATA RATHER THAN RESOLVING FOR REAL.
The honest strongest check is ``uv pip install --dry-run`` over the pin set,
which is what the image does. That needs network and an index, so it is slow and
flaky in CI and would fail for reasons unrelated to the defect -- and a guard
that fails for unrelated reasons gets muted, which is worse than not having it.
Instead this reads the requirement metadata of the ALREADY-INSTALLED
distributions, which CI has because it installs ``.[all,dev]``.

That is a real limitation and it is stated rather than hidden: if a pinned
version differs from the installed one, its requirements may differ too, and
this check reasons about the installed metadata. It therefore catches the case
that actually occurred -- a pin contradicting a requirement that is visible in
the environment -- and does not claim to be a resolver.

TWO THINGS IT DELIBERATELY DOES NOT CHECK, named so nobody reads a pass as more
than it is:

1. That a pinned version EXISTS on PyPI. A typo'd pin resolves to nothing and
   fails the build exactly as loudly as a conflict does. Verifying it needs the
   index, which is the network dependency this module is avoiding.
2. Requirements of a version OTHER than the installed one. If a pin is far from
   what is installed, its real requirements are not in this environment to read.

Both are real gaps. They are written down instead of papered over, because a
guard trusted for more than it measures is worse than no guard -- that is how
2026-08-18 happened, when a passing smoke test (``import scitex_writer.writer``)
was read as proof the image was good while hub actually needed
``scitex_writer.workspace_layout``.
"""

import pathlib
import re

import pytest
from packaging.requirements import Requirement
from packaging.version import InvalidVersion, Version

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
DOCKERFILE = REPO_ROOT / "deployment/docker/docker_prod/Dockerfile.prod"

#: ``"package==1.2.3"`` as it appears in a RUN uv pip install continuation.
_PINNED = re.compile(r'"([A-Za-z0-9_.-]+)==([0-9][^"]*)"')


def _norm(name):
    return name.lower().replace("_", "-")


def _dockerfile_pins():
    """Every ``pkg==version`` the production Dockerfile installs explicitly."""
    return {
        _norm(name): version for name, version in _PINNED.findall(DOCKERFILE.read_text())
    }


def _installed_version(dist_name):
    """Version of the INSTALLED distribution, or None if absent."""
    import importlib.metadata as md

    try:
        return md.version(dist_name)
    except md.PackageNotFoundError:
        return None


def _installed_requirements(dist_name):
    """Requirements declared by the INSTALLED distribution, or None if absent."""
    import importlib.metadata as md

    try:
        raw = md.requires(dist_name)
    except md.PackageNotFoundError:
        return None
    out = []
    for line in raw or []:
        try:
            req = Requirement(line)
        except Exception:
            continue
        # Skip extras-gated requirements: they are not installed unless the
        # extra is requested, so treating them as hard constraints would
        # manufacture conflicts the image never hits.
        if req.marker is not None and "extra" in str(req.marker):
            continue
        out.append(req)
    return out


def _conflicts():
    """Pins contradicted by another pinned package's own declared requirement."""
    pins = _dockerfile_pins()
    bad = []
    for holder, _holder_version in pins.items():
        reqs = _installed_requirements(holder)
        if reqs is None:
            continue
        for req in reqs:
            target = _norm(req.name)
            if target not in pins:
                continue
            pinned = pins[target]
            try:
                version = Version(pinned)
            except InvalidVersion:
                continue
            if not req.specifier.contains(version, prereleases=True):
                # Name the version the requirement was READ FROM. Printing
                # the Dockerfile's pin next to a requirement taken from a
                # DIFFERENT installed version reads as though the pinned
                # version declared it -- which is a false attribution, and one
                # this file made about itself before being corrected.
                bad.append(
                    f"Dockerfile pins {target}=={pinned}, which is contradicted "
                    f"by {holder}'s requirement '{req.name}{req.specifier}' "
                    f"(read from INSTALLED {holder}=={_installed_version(holder)}; "
                    f"the Dockerfile pins {holder}=={pins[holder]})"
                )
    return bad


def test_the_dockerfile_is_readable():
    """Control. A moved path would make everything below vacuously green."""
    # Arrange
    path = DOCKERFILE

    # Act
    exists = path.is_file()

    # Assert
    assert exists, f"{path} is missing; the checks below cannot see anything"


def test_the_pin_scanner_finds_pins():
    """Control on the scanner. A regex matching nothing reports zero conflicts."""
    # Arrange
    pins = _dockerfile_pins()

    # Act
    found = len(pins)

    # Assert
    assert found > 0, "the pin regex matched nothing; a zero-conflict result is meaningless"


def test_at_least_one_pinned_package_is_installed_and_declares_requirements():
    """Control on the DATA SOURCE, which is the one that would silently gut this.

    Every conflict here is found by reading installed metadata. If none of the
    pinned distributions are installed, every lookup returns None, the loop body
    never runs, and the real assertion passes over zero comparisons -- green, and
    proving nothing. This is the same vacuous-pass hazard the sibling guard hit
    when its pyproject parser silently truncated to an empty list.
    """
    # Arrange
    with_reqs = [
        name for name in _dockerfile_pins() if (_installed_requirements(name) or []) != []
    ]

    # Act
    found = len(with_reqs)

    # Assert
    assert found > 0, (
        "no pinned distribution is installed with declared requirements, so this "
        "guard compared nothing. Install .[all,dev] before trusting a pass."
    )


def test_no_pin_contradicts_another_pinned_packages_requirement():
    """The defect itself. FAILS on scitex-ui==0.6.3 with scitex-writer==2.42.0."""
    # Arrange
    conflicts = _conflicts()

    # Act
    report = "\n  ".join(conflicts)

    # Assert
    assert not conflicts, (
        "The Dockerfile pins are not satisfiable together:\n  "
        + report
        + "\n\nThis is what `uv pip install` reports as 'No solution found when "
        "resolving dependencies'. Each pin can be individually correct and still "
        "produce an unbuildable image, which is why the declared-floor guard does "
        "not catch it. Bump the contradicted pin to a version the requirement allows."
    )


@pytest.mark.parametrize("pkg", ["scitex-writer", "scitex-ui"])
def test_the_two_packages_from_the_2026_08_19_failure_are_still_pinned(pkg):
    """If either stops being pinned, the regression this file guards changed shape.

    Not an assertion about versions -- those move. It asserts the guard is still
    pointed at the pair that actually broke the build, so a silent removal does
    not leave a green test guarding nothing.
    """
    # Arrange
    pins = _dockerfile_pins()

    # Act
    present = pkg in pins

    # Assert
    assert present, (
        f"{pkg} is no longer pinned in the Dockerfile. That may be correct, but "
        "update this guard deliberately rather than leaving it asserting a pair "
        "that no longer exists."
    )
