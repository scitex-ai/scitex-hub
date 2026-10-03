"""Django strips single-line {# #} comments but renders multi-line ones
literally (the tag regex does not span newlines), so a multi-line {# #}
leaks onto the page. Multi-line notes must use {% comment %}.
"""

import glob
import os

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _iter_templates():
    patterns = ("templates/**/*.html", "apps/**/templates/**/*.html")
    for pattern in patterns:
        for path in glob.glob(os.path.join(REPO_ROOT, pattern), recursive=True):
            yield path


def test_no_multiline_django_hash_comments():
    offenders = []
    for path in _iter_templates():
        with open(path, encoding="utf-8", errors="ignore") as fh:
            text = fh.read()
        start = 0
        while True:
            open_idx = text.find("{#", start)
            if open_idx == -1:
                break
            close_idx = text.find("#}", open_idx + 2)
            if close_idx == -1:
                offenders.append(path + ": unclosed comment")
                break
            if "\n" in text[open_idx:close_idx]:
                line = text[:open_idx].count("\n") + 1
                offenders.append(f"{path}:{line}")
            start = close_idx + 2
    assert offenders == [], "multi-line {# #} leaks onto pages: %s" % offenders
