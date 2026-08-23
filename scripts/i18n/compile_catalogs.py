#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Compile every .po under locale/ to .mo, WITHOUT gettext tooling.

WHY THIS EXISTS RATHER THAN `django-admin compilemessages`
----------------------------------------------------------
`compilemessages` shells out to `msgfmt`, and msgfmt is NOT INSTALLED where
this project runs. Measured 2026-08-23 in three places:

    scitex-hub agent container      msgfmt ABSENT   babel 2.18.0 present
    scitex-hub-prod-django:latest   msgfmt ABSENT   babel 2.18.0 present
    scitex-app's container          msgfmt ABSENT   babel 2.18.0 present

Three environments, three absences, one common tool. So the pure-Python path
is not a convenience — it is the only one that works anywhere we deploy.

WHY IT MATTERS THAT THIS RUNS AT ALL
------------------------------------
Django resolves a missing translation by returning the msgid, i.e. the English
source string. So a catalog that is present but UNCOMPILED renders exactly like
a catalog nobody has translated yet. Before this script existed, hub declared
Japanese in LANGUAGES, shipped a .po, compiled nothing, and served English —
and every layer reported success. The failure had no symptom other than the
page being in the wrong language.

USAGE
-----
    python scripts/i18n/compile_catalogs.py [--locale-dir DIR] [--check]

    --check   compile nothing; exit non-zero if any .po lacks an up-to-date
              .mo. For CI and for the packaging gate.

Exit codes are deliberate and not overloaded: 0 success, 1 a real failure
(unparseable catalog, or --check found stale output), 2 usage error via argparse.
"""

import argparse
import sys
from pathlib import Path


def _iter_catalogs(locale_dir: Path):
    """Yield every .po under locale_dir, sorted for deterministic output."""
    return sorted(locale_dir.rglob("*.po"))


def compile_catalog(po_path: Path) -> Path:
    """Compile one .po to a sibling .mo. Returns the .mo path.

    Raises rather than returning a status: an unparseable catalog is a build
    failure, not a condition the caller should be free to ignore.
    """
    from babel.messages.mofile import write_mo
    from babel.messages.pofile import read_po

    mo_path = po_path.with_suffix(".mo")
    with po_path.open("r", encoding="utf-8") as handle:
        catalog = read_po(handle, locale=po_path.parent.parent.name)
    with mo_path.open("wb") as handle:
        write_mo(handle, catalog)
    return mo_path


def _is_stale(po_path: Path) -> bool:
    """True if the .mo is missing or older than its .po."""
    mo_path = po_path.with_suffix(".mo")
    if not mo_path.exists():
        return True
    return mo_path.stat().st_mtime < po_path.stat().st_mtime


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--locale-dir",
        default="locale",
        help="root directory holding <lang>/LC_MESSAGES/*.po (default: locale)",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="do not compile; fail if any .mo is missing or stale",
    )
    args = parser.parse_args(argv)

    locale_dir = Path(args.locale_dir)
    if not locale_dir.is_dir():
        print(f"ERROR: locale dir not found: {locale_dir}", file=sys.stderr)
        return 1

    catalogs = _iter_catalogs(locale_dir)
    if not catalogs:
        # An empty locale tree is almost certainly a mistake (wrong --locale-dir,
        # or catalogs not shipped), and silently succeeding here is how the
        # no-compiled-catalog defect got reintroduced. Say so and fail.
        print(f"ERROR: no .po files under {locale_dir}", file=sys.stderr)
        return 1

    if args.check:
        stale = [p for p in catalogs if _is_stale(p)]
        for path in stale:
            print(f"STALE OR MISSING .mo for: {path}", file=sys.stderr)
        if stale:
            print(
                f"FAIL: {len(stale)} of {len(catalogs)} catalog(s) not compiled. "
                f"Run: python {Path(__file__).as_posix()}",
                file=sys.stderr,
            )
            return 1
        print(f"OK: {len(catalogs)} catalog(s) compiled and current.")
        return 0

    for po_path in catalogs:
        mo_path = compile_catalog(po_path)
        size = mo_path.stat().st_size
        print(f"compiled {po_path} -> {mo_path} ({size} bytes)")
    print(f"OK: {len(catalogs)} catalog(s) compiled.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
