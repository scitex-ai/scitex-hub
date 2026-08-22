#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""The half of the preflight that reads hub's OWN declarations.

``scripts/deploy/preflight_declarations.py`` answers "what does hub ask for" and
"what does hub import at module scope"; ``preflight_versions.py`` answers "does
this version satisfy that specifier". Neither touches the deployment -- the
target's answers come from ``preflight_probe.py`` running inside it -- so these
run against hub's real tree and need no environment.

Most of this file is CONTROLS. A parser that returns nothing reports no conflicts
and looks exactly like success, which is the same silent-clean failure mode as an
empty grep: absence is indistinguishable from correctness unless something proves
the reader works. The scan control is not hypothetical for this repo.
"""

import pytest


def test_the_floor_parser_finds_floors_in_the_base_dependency_array(
    preflight_declarations, hub_pyproject
):
    """Control. Zero parsed floors would make every later comparison vacuous."""
    # Arrange
    pyproject = hub_pyproject

    # Act
    narrow = preflight_declarations.declared_floors(pyproject, ())

    # Assert
    assert narrow, "parsed zero floors from [project.dependencies]"


def test_the_floor_parser_also_reads_the_optional_group_the_prod_image_installs(
    preflight_declarations, hub_pyproject
):
    """The widening that the OLD static guard does not do.

    tests/deployment/test_dockerfile_pins_satisfy_declared_floors.py reads only
    the ``dependencies = [`` array, so it cannot see scitex-ui, figrecipe or
    scitex-cards -- all of which live in optional groups while the prod image
    installs ``.[all]`` (Dockerfile.prod). A narrow parser is green on exactly the
    packages it never compared.
    """
    # Arrange
    narrow = preflight_declarations.declared_floors(hub_pyproject, ())

    # Act
    wide = preflight_declarations.declared_floors(hub_pyproject, ("all",))

    # Assert
    assert len(wide) > len(narrow), (
        "including the 'all' extra added no floors; either the extra moved or the "
        "parser stopped at the base array, which is the bug this exists to avoid"
    )


def test_a_missing_extra_is_an_error_rather_than_an_empty_result(
    preflight_declarations, hub_pyproject
):
    """If the group the prod image installs is renamed, the preflight must SAY so.

    Silently returning the base dependencies would leave the gate running, green,
    and comparing a strictly smaller set than the image installs.
    """
    # Arrange
    absent_group = "no-such-extra-group"

    # Act
    call = lambda: preflight_declarations.declared_floors(hub_pyproject, (absent_group,))  # noqa: E731

    # Assert
    with pytest.raises(preflight_declarations.DeclarationError):
        call()


def test_the_import_scan_actually_reads_files(real_repo_scan):
    """Control. An empty scan result and a scanner that read nothing look identical."""
    # Arrange
    _found, files_scanned = real_repo_scan

    # Act
    enough = files_scanned > 100

    # Assert
    assert enough, "scanned only {0} files; the scan is vacuous".format(files_scanned)


def test_the_import_scan_finds_something(real_repo_scan):
    """Control. hub imports siblings at module scope in several places; finding
    none would mean the predicate, not the codebase, changed."""
    # Arrange
    found, _files_scanned = real_repo_scan

    # Act
    any_found = len(found) > 0

    # Assert
    assert any_found


def test_the_import_scan_finds_the_import_that_caused_the_20260818_outage(real_repo_scan):
    """The known positive instance. A scanner that cannot find the import which
    already caused an outage will not find the next one."""
    # Arrange
    found, _files_scanned = real_repo_scan

    # Act
    modules = {item.module for item in found}

    # Assert
    assert "scitex_writer.workspace_layout" in modules


def test_the_20260818_import_is_classified_as_unguarded(real_repo_scan):
    """Unguarded is what makes it an outage rather than a degraded feature: it runs
    at module scope with no try/except, so a missing symbol stops Django booting.
    Misclassifying it as guarded would demote the finding to advisory."""
    # Arrange
    found, _files_scanned = real_repo_scan
    modules = {item.module: item for item in found}

    # Act
    guarded = modules["scitex_writer.workspace_layout"].guarded

    # Assert
    assert guarded is False


def test_a_try_except_importerror_import_is_classified_as_guarded(real_repo_scan):
    """The other pole of the classifier. ``scitex_live_paper`` is deliberately
    guarded and deliberately absent in prod today; treating it as fatal would make
    the gate red on every deploy for a condition hub already handles."""
    # Arrange
    found, _files_scanned = real_repo_scan
    modules = {item.module: item for item in found}

    # Act
    guarded = modules["scitex_live_paper"].guarded

    # Assert
    assert guarded is True


def test_hub_is_not_asked_about_its_own_packages(real_repo_scan):
    """hub's own wheel provides scitex_hub and scitex_cloud, and importlib.metadata
    maps scitex_container to BOTH scitex-hub and scitex-container. Probing them
    asks the target about hub's own source tree, which is not a sibling floor."""
    # Arrange
    found, _files_scanned = real_repo_scan

    # Act
    roots = {item.module.split(".")[0] for item in found}

    # Assert
    assert not ({"scitex_hub", "scitex_cloud"} & roots)


@pytest.mark.parametrize(
    "version,specifier,expected",
    [
        ("2.41.0", ">=2.42.0", False),
        ("2.42.0", ">=2.42.0", True),
        ("2.42.1", ">=2.42.0", True),
        ("0.55.0", "==0.43.1", False),
        ("2.29.3", ">=2.29.3", True),
        ("0.4.0", ">=0.5.0", False),
        ("2.42.0rc1", ">=2.42.0", False),
        ("1.2", ">=1.2.0", True),
        ("0.34.6", ">=0.34.6,<1.0", True),
    ],
)
def test_the_builtin_comparator_matches_pep440_on_the_cases_hub_declares(
    preflight_versions, version, specifier, expected
):
    """The deploy host is not guaranteed to have ``packaging``, so the fallback is
    exercised directly rather than only when the host happens to lack it. Every
    case here is a real specifier from hub's pyproject or a real prod version."""
    # Arrange
    subject = (version, specifier)

    # Act
    result = preflight_versions._satisfies_builtin(subject[0], subject[1])

    # Assert
    assert result is expected


def test_an_unparseable_version_is_undecidable_rather_than_false(preflight_versions):
    """Answering False would report a floor as violated for a reason that is not
    true; answering True would hide one. Refusing to decide is the only honest
    third value, and the driver turns it into a refusal."""
    # Arrange
    bad = "not-a-version"

    # Act
    call = lambda: preflight_versions._satisfies_builtin(bad, ">=1.0")  # noqa: E731

    # Assert
    with pytest.raises(preflight_versions.Undecidable):
        call()


def test_an_unparseable_specifier_is_undecidable_rather_than_true(preflight_versions):
    """The mirror case. A malformed specifier that quietly returned True would
    silently drop that package out of the comparison."""
    # Arrange
    nonsense = "definitely not a specifier"

    # Act
    call = lambda: preflight_versions._satisfies_builtin("1.0.0", nonsense)  # noqa: E731

    # Assert
    with pytest.raises(preflight_versions.Undecidable):
        call()

# EOF
