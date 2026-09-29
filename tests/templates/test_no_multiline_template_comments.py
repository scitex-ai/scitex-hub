"""No multi-line ``{# ... #}`` comments in any template.

Django's ``{# #}`` is SINGLE-LINE ONLY: a multi-line one is never lexed as
a comment and renders VERBATIM into the page (this fired for real on the
signup page, leaking a developer note about card fields to visitors).
Multi-line notes must use ``{% comment %}``.
"""

import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
TEMPLATE_DIRS = [REPO / "templates", REPO / "apps"]

MULTILINE_COMMENT = re.compile(r"\{#(.*?)#\}", re.S)


def _template_files():
    for base in TEMPLATE_DIRS:
        if not base.is_dir():
            continue
        yield from base.rglob("*.html")


def test_no_multiline_hash_comments():
    offenders = []
    for path in _template_files():
        text = path.read_text(encoding="utf-8", errors="replace")
        for match in MULTILINE_COMMENT.finditer(text):
            if "\n" in match.group(1):
                line = text[: match.start()].count("\n") + 1
                offenders.append(f"{path.relative_to(REPO)}:{line}")
    assert not offenders, (
        "multi-line {# #} renders verbatim — use {% comment %}: "
        + ", ".join(sorted(offenders))
    )
