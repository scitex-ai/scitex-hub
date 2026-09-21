#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: tests/config/test_i18n_legal_terms.py
"""Terms of Use: every {% trans %} string must actually be Japanese under ja.

WHY THIS FILE EXISTS
--------------------
`/terms/` was found serving a MIXED-LANGUAGE page on 2026-09-21. Thirteen
strings of the page had no Japanese entry at all, including the three clauses
that carry the most legal weight:

  * "These Terms of Use constitute a legally binding agreement ..."
  * "Unless otherwise indicated, the SciTeX platform is our proprietary
     property ..." (IP ownership)
  * "You retain all rights to your research data, documents, code ..."
     (user-content rights)

and the whole "Compute Usage and Storage" section newly added by 8d5e60ecb
(Terms of Use, /tmp vs /scratch). A Japanese reader got Japanese headings with
English bodies underneath them, in the middle of a binding agreement.

Nothing failed, because Django resolves a missing translation by returning the
msgid — the English source string. An untranslated page and a correctly
translated English page render IDENTICALLY. That is why this is a coverage
assertion over the template's own strings rather than a spot-check of two
headings: a spot-check passes the moment anyone adds one entry.

THE ONE DISTINCTION THIS FILE MAKES
-----------------------------------
An entry whose msgstr equals its msgid is an EXPLICIT PASS-THROUGH — the
translator's way of saying "this string is correct as-is", which on this page
is the right call for the four payment brand marks (Visa, Mastercard, American
Express, Discover are trademarks and are written in Latin script). An entry
that is ABSENT, or present with an empty msgstr, is a GAP. Conflating the two
would either fail on a correct page or silently accept a missing clause.

The pass-through list is asserted EXACTLY, so adding a new one is a deliberate
act that shows up in review rather than a way to make this test quiet.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import pytest
from babel.messages import pofile
from django.utils import translation

PROJECT_ROOT = Path(__file__).resolve().parents[2]
TERMS_TEMPLATE = (
    PROJECT_ROOT
    / "apps"
    / "infra"
    / "public_app"
    / "templates"
    / "public_app"
    / "legal"
    / "terms_of_use.html"
)
JA_CATALOG = PROJECT_ROOT / "locale" / "ja" / "LC_MESSAGES" / "django.po"

# Trademarks, deliberately left in Latin script. Exactly these four — see the
# module docstring for why this list is asserted rather than ignored.
PASS_THROUGH = {"Visa", "Mastercard", "American Express", "Discover"}

# The strings that were missing when this defect was found. Named individually
# so that a future regression identifies itself instead of only moving a count.
COMPUTE_USAGE_HEADING = "Compute Usage and Storage"
BINDING_AGREEMENT_PREFIX = "These Terms of Use constitute a legally binding agreement"
IP_OWNERSHIP_PREFIX = "Unless otherwise indicated, the SciTeX platform is our proprietary property"
USER_CONTENT_RIGHTS_PREFIX = "You retain all rights to your research data"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture(scope="module", autouse=True)
def compiled_catalogs():
    """Compile locale/**/*.po -> .mo before assertions read a catalog.

    `*.mo` is gitignored, so a fresh checkout has source catalogs only. This
    runs the project's own compile step rather than `compilemessages`, because
    msgfmt is absent from this container and from the prod image; see
    scripts/i18n/compile_catalogs.py for the measurements.
    """
    # Arrange
    script = PROJECT_ROOT / "scripts" / "i18n" / "compile_catalogs.py"
    # Act
    result = subprocess.run(
        [sys.executable, str(script)],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
    )
    # Assert
    assert result.returncode == 0, (
        f"catalog compilation failed ({result.returncode}):\n"
        f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )
    # Django caches translation objects per language; anything loaded before
    # the .mo existed would be an empty catalog that never reloads.
    translation.trans_real._translations.clear()
    yield


def _template_trans_strings() -> list[str]:
    """Every distinct {% trans "..." %} literal, in template order."""
    source = TERMS_TEMPLATE.read_text(encoding="utf-8")
    seen: list[str] = []
    for match in re.findall(r'\{%\s*trans\s+"((?:[^"\\]|\\.)*)"\s*%\}', source):
        if match not in seen:
            seen.append(match)
    return seen


def _ja_catalog() -> dict[str, str]:
    with JA_CATALOG.open("rb") as handle:
        catalog = pofile.read_po(handle)
    return {message.id: message.string for message in catalog if message.id}


# ---------------------------------------------------------------------------
# The coverage gate
# ---------------------------------------------------------------------------
def test_terms_of_use_template_actually_has_translatable_strings():
    """A guard on the guard: this test is meaningless if extraction finds none.

    If someone reformats the template such that the regex stops matching, every
    assertion below would iterate an empty list and pass.
    """
    # Arrange
    floor = 50
    # Act
    strings = _template_trans_strings()
    # Assert
    assert len(strings) >= floor, (
        f"only {len(strings)} {{% trans %}} strings found in {TERMS_TEMPLATE.name} "
        f"(expected >= {floor}) — extraction is broken, not the page"
    )


def test_every_terms_string_has_a_japanese_entry():
    """No absent and no empty msgstr, except the declared brand pass-throughs."""
    # Arrange
    catalog = _ja_catalog()
    strings = _template_trans_strings()
    # Act
    missing = [s for s in strings if s not in catalog or catalog[s] in ("", None)]
    # Assert
    assert not missing, (
        f"{len(missing)} string(s) on /terms/ have no Japanese entry, so the page "
        f"renders them in English under `ja`:\n"
        + "\n".join(f"  - {s[:110]!r}" for s in missing)
    )


def test_japanese_page_is_not_english_with_extra_steps():
    """Every non-pass-through string must actually RESOLVE to something else.

    A catalog can hold an entry that still renders English — for example a
    duplicated msgid, where gettext takes the first and the second is dead.
    That is not hypothetical: it happened while writing this fix.
    """
    # Arrange
    catalog = _ja_catalog()
    strings = _template_trans_strings()
    # Act
    untranslated = [
        s
        for s in strings
        if s not in PASS_THROUGH and catalog.get(s) == s
    ]
    # Assert
    assert not untranslated, (
        f"{len(untranslated)} string(s) have a msgstr identical to the msgid "
        f"without being declared pass-through, i.e. still English under `ja`:\n"
        + "\n".join(f"  - {s[:110]!r}" for s in untranslated)
    )


def test_pass_through_list_is_exactly_the_trademarks():
    """Adding a fifth pass-through must be a visible, deliberate act."""
    # Arrange
    catalog = _ja_catalog()
    strings = _template_trans_strings()
    # Act
    declared = {s for s in strings if catalog.get(s) == s}
    # Assert
    assert declared == PASS_THROUGH, (
        "the set of strings that render unchanged under `ja` has changed; if this "
        "is intentional, update PASS_THROUGH in this file:\n"
        f"  new: {sorted(declared - PASS_THROUGH)}\n"
        f"  gone: {sorted(PASS_THROUGH - declared)}"
    )


# ---------------------------------------------------------------------------
# The specific clauses this change repaired
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "prefix",
    [
        COMPUTE_USAGE_HEADING,
        BINDING_AGREEMENT_PREFIX,
        IP_OWNERSHIP_PREFIX,
        USER_CONTENT_RIGHTS_PREFIX,
        "Shared Temporary Space",
        "Private Working Storage",
        "Why the Distinction Exists",
    ],
)
def test_repaired_clause_resolves_to_japanese(prefix):
    """Each clause that was English-on-a-Japanese-page now resolves to Japanese."""
    # Arrange
    catalog = _ja_catalog()
    matches = [s for s in _template_trans_strings() if s.startswith(prefix)]
    assert matches, f"no string on /terms/ starts with {prefix!r} — template drift"
    # Act
    with translation.override("ja"):
        resolved = translation.gettext(matches[0])
    # Assert
    assert resolved != matches[0], (
        f"{prefix!r} still resolves to its English source under `ja`"
    )
    assert re.search(r"[\u3040-\u30ff\u4e00-\u9fff]", resolved), (
        f"{prefix!r} resolved to {resolved[:60]!r}, which contains no kana or kanji"
    )


def test_render_is_language_sensitive_both_ways():
    """The paired control: ja gives Japanese, en gives English — same string.

    Without the `en` half, this file would still pass if the catalog translated
    unconditionally, and it would not prove the RENDER depends on the locale.
    """
    # Arrange
    source = COMPUTE_USAGE_HEADING
    # Act
    with translation.override("ja"):
        ja = translation.gettext(source)
    with translation.override("en"):
        en = translation.gettext(source)
    # Assert
    assert ja != source, "under `ja` the section heading is still the English source"
    assert en == source, f"under `en` the heading resolved to {en!r}, not the English source"
    assert ja != en, "both locales resolved identically — the catalog is not locale-scoped"
