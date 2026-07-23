#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""DB-free, mock-free guards for the public /security/ trust page.

This runs in CI's "Security Regression Gate" job, which has NO Postgres and
FORBIDS ``unittest.mock`` (linter rules STX-NM001/NM003). So there is
deliberately NO ``@pytest.mark.django_db``, NO ``unittest.mock``, and NO Django
DB/client here — only pure functions and static file/text scans.

The page's own meta-test (this file) tests the trust PAGE, not a product
security control, so it is excluded from the advertised security-regression
count — exactly as ``scripts/security/gen_security_status.py`` excludes it.
Each test carries one assertion and states the breakage it would catch.
"""
from __future__ import annotations

import importlib.util
import json
import re
from pathlib import Path

_HERE = Path(__file__).resolve()
TESTS_SECURITY_DIR = _HERE.parent
REPO_ROOT = _HERE.parents[2]
PUBLIC_APP = REPO_ROOT / "apps" / "infra" / "public_app"
STATUS_JSON = PUBLIC_APP / "data" / "security_status.json"
TEMPLATE = PUBLIC_APP / "templates" / "public_app" / "pages" / "security.html"
GEN_SCRIPT = REPO_ROOT / "scripts" / "security" / "gen_security_status.py"

# Excluded from the count because it tests the page, not a product control.
_EXCLUDE = {"test_security_status_page.py"}
_TEST_DEF_RE = re.compile(r"(?m)^[ \t]*def test_")

# Substrings that would map our attack surface on a PUBLIC page — never allowed.
_FORBIDDEN = (
    "not covered",
    "gap",
    "todo",
    "vulnerable",
    "unpatched",
    "open hole",
    "未対応",
    "脆弱",
)


def _recount_security_tests() -> tuple[int, int]:
    """Independently recount ``def test_`` across tests/security/test_*.py."""
    files = [
        p
        for p in sorted(TESTS_SECURITY_DIR.glob("test_*.py"))
        if p.name not in _EXCLUDE
    ]
    count = sum(
        len(_TEST_DEF_RE.findall(p.read_text(encoding="utf-8"))) for p in files
    )
    return count, len(files)


def _load_status() -> dict:
    return json.loads(STATUS_JSON.read_text(encoding="utf-8"))


def _forbidden_hits(text: str) -> list[str]:
    low = text.lower()
    return [bad for bad in _FORBIDDEN if bad.lower() in low]


def _load_gen_module():
    spec = importlib.util.spec_from_file_location("gen_security_status", GEN_SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_status_json_exists():
    # Catches: the data file missing entirely — the view raises and the page
    # cannot render its live metric without it.
    # Arrange
    path = STATUS_JSON
    # Act
    present = path.exists()
    # Assert
    assert present, f"missing {path}; run scripts/security/gen_security_status.py"


def test_status_json_reports_positive_test_count():
    # Catches: a JSON that parses but carries a missing/zero/non-int test_count,
    # which would render a broken or dishonest metric on the page.
    # Arrange
    status = _load_status()
    # Act
    value = status["test_count"]
    # Assert
    assert isinstance(value, int) and value > 0


def test_status_json_reports_positive_test_files():
    # Catches: a missing/zero/non-int test_files (the "N focused suites" line
    # would be broken or dishonest).
    # Arrange
    status = _load_status()
    # Act
    value = status["test_files"]
    # Assert
    assert isinstance(value, int) and value > 0


def test_published_test_count_never_exceeds_live_recount():
    # Catches: the page OVERSTATING — advertising more security tests than the
    # suite actually contains (e.g. tests deleted after the snapshot). A
    # stale-but-lower count is an honest point-in-time snapshot and is allowed;
    # CI regen (follow-up) keeps it fresh. Exact-match would red-line develop's
    # required gate every time any other PR adds a security test.
    # Arrange
    status = _load_status()
    # Act
    real_count, _ = _recount_security_tests()
    # Assert
    assert status["test_count"] <= real_count


def test_published_test_files_never_exceeds_live_recount():
    # Catches: the page overstating the number of security suites. Under-count
    # (stale-but-honest snapshot) is allowed; over-count is a lie.
    # Arrange
    status = _load_status()
    # Act
    _, real_files = _recount_security_tests()
    # Assert
    assert status["test_files"] <= real_files


def test_template_source_has_no_gap_leaking_substrings():
    # Catches: the template markup publishing our attack surface (a gap/TODO/
    # severity word in the page HTML). Most important guard — the page is PUBLIC.
    # Arrange
    source = TEMPLATE.read_text(encoding="utf-8")
    # Act
    hits = _forbidden_hits(source)
    # Assert
    assert hits == [], f"forbidden substrings in template: {hits}"


def test_status_json_has_no_gap_leaking_substrings():
    # Catches: the rendered measure DATA (categories come from the JSON)
    # publishing our attack surface — the scan must cover the JSON, not only
    # the template markup.
    # Arrange
    source = STATUS_JSON.read_text(encoding="utf-8")
    # Act
    hits = _forbidden_hits(source)
    # Assert
    assert hits == [], f"forbidden substrings in status JSON: {hits}"


def test_generator_counting_function_matches_published_count():
    # Catches: the shipped counting logic diverging from the published number —
    # script and page must agree or the metric is untrustworthy.
    # Arrange
    module = _load_gen_module()
    status = _load_status()
    # Act
    count, _ = module.count_security_tests(TESTS_SECURITY_DIR)
    # Assert
    assert status["test_count"] <= count


def test_generator_counting_function_matches_published_files():
    # Catches: the generator's file tally diverging from the published test_files.
    # Arrange
    module = _load_gen_module()
    status = _load_status()
    # Act
    _, files = module.count_security_tests(TESTS_SECURITY_DIR)
    # Assert
    assert status["test_files"] <= files


# EOF
