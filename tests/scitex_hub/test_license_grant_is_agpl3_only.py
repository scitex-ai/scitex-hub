"""The licence SciTeX GRANTS must match the licence it DECLARES.

Operator decision 2026-08-01 (Telegram):「オンリーに揃えるです」 — align on
AGPL-3.0-only. The same correction was already made on `main` as 02f84ff61 and
never came back to develop, which is how the two drifted apart.

Two places state the grant, and BOTH must say "only":

  LICENSE                              the How-to-Apply template
  src/scitex_hub/appmaker/_license.py  AGPL3_NOTICE — stamped into every
                                       app the generator emits

``test_agpl_body_text_still_offers_or_later`` is a POSITIVE CONTROL and is the
reason this file is not a one-liner. The phrase "any later version" also appears
in the AGPL's own body (§14, describing what that phrase means when a program
uses it). That text IS the licence. A regex sweep for the phrase would rewrite
it and produce a document that is no longer the AGPL — while passing every
naive "did we remove or-later?" check. The control asserts the body still has
it. Read the two together: template without, body with. Either alone is
satisfiable by a wrong change.
"""

from __future__ import annotations

import tomllib
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]

# Where the AGPL's own body ends and the copy-paste template begins.
_HOWTO_HEADING = "How to Apply These Terms to Your New Programs"

_OR_LATER = "any later version"
_ONLY = "version 3 of the License only"


@pytest.fixture(name="license_sections")
def _license_sections() -> tuple[str, str]:
    """Split LICENSE into (agpl_body, howto_template).

    Fails loudly rather than returning empties: a split that silently produced
    two blank strings would make every assertion in this file pass vacuously.
    """
    text = (REPO / "LICENSE").read_text(encoding="utf-8")
    if _HOWTO_HEADING not in text:
        raise AssertionError(
            f"LICENSE no longer contains the anchor {_HOWTO_HEADING!r}, so this "
            "guard cannot tell the AGPL body from the How-to-Apply template. "
            "Fix the anchor before trusting any result from this file."
        )
    body, _, howto = text.partition(_HOWTO_HEADING)
    if not body.strip() or not howto.strip():
        raise AssertionError(
            "Splitting LICENSE on the How-to-Apply heading produced an empty "
            "section, so the guard below would pass without checking anything."
        )
    return body, howto


def test_pyproject_declares_agpl_3_only() -> None:
    """pyproject is the declaration every grant below has to match."""
    # Arrange
    text = (REPO / "pyproject.toml").read_text(encoding="utf-8")
    # Act
    declared = tomllib.loads(text)["project"]["license"]
    # Assert
    assert declared == "AGPL-3.0-only"


def test_howto_template_states_version_3_only(
    license_sections: tuple[str, str],
) -> None:
    """The template a downstream author copies must name the narrow grant."""
    # Arrange
    _body, howto = license_sections
    # Act
    states_only = _ONLY in howto
    # Assert
    assert states_only, (
        f"LICENSE's How-to-Apply template does not say {_ONLY!r}. It must "
        "match pyproject's AGPL-3.0-only declaration."
    )


def test_howto_template_does_not_offer_or_later(
    license_sections: tuple[str, str],
) -> None:
    """...and must not also offer the broader grant."""
    # Arrange
    _body, howto = license_sections
    # Act
    offers_or_later = _OR_LATER in howto
    # Assert
    assert not offers_or_later, (
        f"LICENSE's How-to-Apply template still offers {_OR_LATER!r}, which "
        "grants more than pyproject declares."
    )


def test_agpl_body_text_still_offers_or_later(
    license_sections: tuple[str, str],
) -> None:
    """POSITIVE CONTROL — the AGPL's own §14 text must survive the fix.

    If this fails, the phrase was swept globally and the licence itself has
    been edited. That is worse than the bug this file exists to catch.
    """
    # Arrange
    body, _howto = license_sections
    # Act
    body_intact = _OR_LATER in body
    # Assert
    assert body_intact, (
        f"The AGPL body no longer contains {_OR_LATER!r}. The licence text "
        "itself has been altered — revert."
    )


def test_generator_notice_states_version_3_only() -> None:
    """The generator is the root cause: it stamps the grant into every app."""
    # Arrange
    from scitex_hub.appmaker._license import AGPL3_NOTICE

    # Act
    states_only = _ONLY in AGPL3_NOTICE
    # Assert
    assert states_only, (
        f"appmaker's AGPL3_NOTICE does not say {_ONLY!r}, so every generated "
        "app would carry a broader grant than SciTeX declares."
    )


def test_generator_notice_does_not_offer_or_later() -> None:
    """...and must not also offer the broader grant."""
    # Arrange
    from scitex_hub.appmaker._license import AGPL3_NOTICE

    # Act
    offers_or_later = _OR_LATER in AGPL3_NOTICE
    # Assert
    assert not offers_or_later, (
        f"appmaker's AGPL3_NOTICE still offers {_OR_LATER!r}."
    )
