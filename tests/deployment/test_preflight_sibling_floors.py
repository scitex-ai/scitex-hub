#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""The deploy gate must be able to go RED, and this proves it can.

``scripts/deploy/preflight_sibling_floors.py`` refuses a container recreate whose
target cannot satisfy hub's declared floors. A gate that has never been observed
failing is worse than no gate, because it licenses the next deploy with an
authority it has not earned -- which is how the 2026-08-18 and 2026-08-22 outages
both reached production past checks that were technically present.

Both poles of both incident shapes are exercised here, against real constructed
environments built by conftest.py:

  ``below_floor`` / ``at_floor``
      the 2026-08-18 shape -- declared ``>=2.42.0``, target holds ``2.41.0``, then
      the identical fixture with ``2.42.0``.

  ``undeclared_absent`` / ``undeclared_present``
      the 2026-08-22 shape -- the missing package is declared in NO pyproject, so
      the floor half stays green and only executing the import finds it. Two
      separate tests assert both halves, because "it refused" and "a floors-only
      check would NOT have refused" are different claims and the second is the
      one that justifies the import probe existing at all.

Readers of hub's own declarations, and the version comparator, are tested in
test_preflight_declarations.py.
"""

# ------------------------------------------------------------------- controls


def test_the_probe_source_is_valid_python(preflight_probe_path):
    """Control. The driver ships this file's TEXT into the target; if it does not
    compile, every target reports 'unreachable' and every red below proves nothing."""
    # Arrange
    source = preflight_probe_path.read_text(encoding="utf-8")

    # Act
    compiled = compile(source, str(preflight_probe_path), "exec")

    # Assert
    assert compiled is not None


def test_the_constructed_target_can_answer_at_all(harness_control):
    """Control on the HARNESS. Every red below would also be produced by a target
    that cannot run Python, so one green through the identical path is required."""
    # Arrange
    code, output = harness_control

    # Act
    passed = code == 0

    # Assert
    assert passed, output


def test_the_control_run_reports_a_satisfied_verdict(harness_control):
    """The green pole must say so in words, not merely exit zero."""
    # Arrange
    _code, output = harness_control

    # Act
    verdict = "satisfies every declared sibling floor" in output

    # Assert
    assert verdict, output


# -------------------------------------------------------- the 2026-08-18 shape


def test_it_refuses_when_the_target_is_below_a_declared_floor(below_floor):
    """RED. Declared >=2.42.0, target holds 2.41.0 -- the outage, reproduced."""
    # Arrange
    code, output = below_floor

    # Act
    refused = code == 1

    # Assert
    assert refused, output


def test_the_floor_refusal_names_the_offending_package(below_floor):
    # Arrange
    _code, output = below_floor

    # Act
    named = "demosib-writer" in output

    # Assert
    assert named, output


def test_the_floor_refusal_names_the_declared_floor(below_floor):
    """'Something is wrong' is not actionable; the declared floor is half the fix."""
    # Arrange
    _code, output = below_floor

    # Act
    named = ">=2.42.0" in output

    # Assert
    assert named, output


def test_the_floor_refusal_names_what_the_target_actually_has(below_floor):
    """The other half. Wanted-without-found sends the reader back to the machine."""
    # Arrange
    _code, output = below_floor

    # Act
    named = "2.41.0" in output

    # Assert
    assert named, output


def test_the_floor_refusal_states_a_remedy(below_floor):
    """An error that only says what broke is half-written."""
    # Arrange
    _code, output = below_floor

    # Act
    has_remedy = "remedy" in output

    # Assert
    assert has_remedy, output


def test_it_passes_on_the_same_floor_once_the_target_satisfies_it(at_floor):
    """GREEN. Same everything except the one version -- both poles, one fixture."""
    # Arrange
    code, output = at_floor

    # Act
    passed = code == 0

    # Assert
    assert passed, output


def test_the_satisfied_floor_run_reports_no_unsatisfied_section(at_floor):
    # Arrange
    _code, output = at_floor

    # Act
    clean = "FLOOR UNSATISFIED" not in output

    # Assert
    assert clean, output


# -------------------------------------------------------- the 2026-08-22 shape


def test_it_refuses_on_an_import_that_no_floor_check_could_see(undeclared_absent):
    """RED on an undeclared transitive dependency -- the 2026-08-22 shape."""
    # Arrange
    code, output = undeclared_absent

    # Act
    refused = code == 1

    # Assert
    assert refused, output


def test_the_import_refusal_names_the_module_that_could_not_be_imported(undeclared_absent):
    # Arrange
    _code, output = undeclared_absent

    # Act
    named = "demosib_umbrella.io" in output

    # Assert
    assert named, output


def test_the_import_refusal_names_the_missing_dependency(undeclared_absent):
    """The reader needs the package to install, not just the module that failed."""
    # Arrange
    _code, output = undeclared_absent

    # Act
    named = "demosib_hidden_dep" in output

    # Assert
    assert named, output


def test_a_floors_only_preflight_would_have_licensed_this_deploy(undeclared_absent):
    """The load-bearing assertion of this file.

    On 2026-08-22 nine of hub's ten declared floors were satisfied in prod and the
    tenth violation was unrelated. If the floor half goes red here too, this
    fixture no longer demonstrates that floors alone are blind to that shape, and
    the import probe loses its justification.
    """
    # Arrange
    _code, output = undeclared_absent

    # Act
    floors_were_green = "FLOOR UNSATISFIED" not in output

    # Assert
    assert floors_were_green, output


def test_it_passes_once_the_undeclared_transitive_is_present(undeclared_present):
    """GREEN. Same fixture, one package added to the target."""
    # Arrange
    code, output = undeclared_present

    # Act
    passed = code == 0

    # Assert
    assert passed, output


def test_a_lazy_attribute_touch_is_probed_and_not_just_the_import(lazy_attribute):
    """The umbrella defers to ``__getattr__``, so importing it is not the question.

    Measured 2026-08-22: ``import scitex`` left 29 sibling distributions loaded and
    one ``stx.plt.load_style()`` pulled six more. A probe that stops at the import
    passes on the artifact that 500s.
    """
    # Arrange
    code, output = lazy_attribute

    # Act
    refused = code == 1

    # Assert
    assert refused, output


def test_the_lazy_attribute_refusal_quotes_the_targets_own_error(lazy_attribute):
    # Arrange
    _code, output = lazy_attribute

    # Act
    quoted = "demosib_plt is required" in output

    # Assert
    assert quoted, output


# ------------------------------------------------ refusing to lie about scope


def test_local_target_says_in_capitals_that_it_is_not_a_target_check(local_target_run):
    """Non-negotiable B. The 2026-08-18 incident happened because a package was
    verified in an agent's own container and the result was stated about prod, so
    the one mode that CAN reproduce that mistake has to disown its own answer."""
    # Arrange
    _code, output = local_target_run

    # Act
    disowned = "THIS IS NOT A TARGET CHECK" in output

    # Assert
    assert disowned, output


def test_an_unreachable_target_is_a_refusal_not_a_pass(unreachable_target):
    """Three-valued. Unknown is not OK -- an unanswerable target must abort the
    deploy, or the gate is a no-op on exactly the day docker misbehaves."""
    # Arrange
    code, output = unreachable_target

    # Act
    aborted = code == 2

    # Assert
    assert aborted, output


def test_the_unreachable_message_says_the_target_could_not_be_interrogated(unreachable_target):
    # Arrange
    _code, output = unreachable_target

    # Act
    explained = "could not be interrogated" in output

    # Assert
    assert explained, output

# EOF
