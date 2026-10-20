#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""The retired Git sidebar stays retired.

`writer_app/index_partials/sidebar.html` was a second, stale copy of the Writer
sidebar, and it was the ONLY template carrying a "Git / Version History Timeline"
section (`#history-timeline-container`). Nothing rendered it: no include, no view,
no URL, no JS fetch, anywhere in the repository. Its Git section was therefore a
surface in the inventory that no user could ever reach — while the live
`shared/_sidebar.html` has no Git section at all.

This is a guard, not a general reachability analyser: a full one would need an
allowlist of legitimately-unreferenced templates, and allowlists rot. What it
does assert is that the specific dead duplicate does not come back and that
nothing starts referencing its path again.

Adjacent finding, NOT fixed here: `id="init-writer-btn"` appears only in the file
being removed, while `static/writer_app/ts/modules/workspace-init.ts` looks that id
up — so that module wires a button no live template provides. Removing the
template changes nothing about it (it was already dangling); the JS hook is left
for its own change rather than folded into a deletion.
"""

from pathlib import Path


REPO = Path(__file__).resolve().parents[4]
DEAD_SURFACE = REPO / "apps/workspace/writer_app/templates/writer_app/index_partials/sidebar.html"
REFERENCE = "index_partials/sidebar"
# CODE only. Documentation is allowed — and expected — to name the retired path:
# the Git-surface inventory in writer_app/README.md records the retirement, and a
# guard that forbade that would force the inventory to forget what it retired.
CODE_SUFFIXES = {".html", ".py", ".ts", ".js", ".css", ".json"}
SCANNED_SUFFIXES = CODE_SUFFIXES | {".md"}
SKIPPED_DIRS = {".git", "node_modules", "__pycache__", ".venv", "staticfiles", ".pytest_cache"}


def _files_mentioning(needle: str) -> list[str]:
    """Files of CODE that mention ``needle``. Documentation is not code."""
    hits: list[str] = []
    for path in REPO.rglob("*"):
        if not path.is_file() or path.suffix not in CODE_SUFFIXES:
            continue
        if any(part in SKIPPED_DIRS for part in path.parts):
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:  # unreadable is not a reason to fail the guard
            continue
        if needle in text:
            hits.append(str(path.relative_to(REPO)))
    return hits


def test_the_dead_git_sidebar_is_gone():
    # Arrange / Act / Assert
    assert not DEAD_SURFACE.exists(), (
        "the stale sidebar template is back; it was unreachable, and it carried the "
        "only Git/Version-History section in writer_app"
    )


def test_nothing_references_the_retired_path_again():
    # Arrange / Act: this test file names the path on purpose, so it is excluded.
    hits = [h for h in _files_mentioning(REFERENCE) if not h.endswith(Path(__file__).name)]
    # Assert
    assert hits == [], f"something references the retired sidebar path: {hits}"


def test_the_guard_can_actually_see_references():
    # Arrange / Act: a guard that cannot find a needle it knows is there would pass
    # for the wrong reason — the failure mode that made a whole class of earlier
    # checks useless.
    known = _files_mentioning("details_panel.html")
    # Assert
    assert known, "the reference scan found nothing at all — it is not looking where it should"


# EOF
