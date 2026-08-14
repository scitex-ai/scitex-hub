#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Path containment — the one place that decides whether a caller-supplied path
fragment is allowed to name a file under a server-side root.

WHY THIS MODULE EXISTS
----------------------
The same four-line guard (`(root / frag).resolve().relative_to(root.resolve())`
inside a try/except) was written out by hand in more than a dozen modules. Two
things follow from that, and both were live in this repo:

1. It drifts. `apps/workspace/apps_app/views/dev_project_files.py` had it
   right — resolve first, then decide. `apps/workspace/repo_app/views/
   api_browse.py` had the same lines in the WRONG ORDER: it called
   `.exists()` / `.is_file()` on the joined path and only checked containment
   afterwards, so a traversal fragment was still answered with a truthful
   "found" / "not found" before anything rejected it. That is an existence
   oracle for paths outside the root.
2. It gets forgotten. `apps/infra/a2a_app/_card.py` joined a URL-supplied
   agent name to the agents directory with no containment check at all.

A guard that must be remembered is forgotten exactly when it matters, so this
module makes the safe operation the easy one to call.

CONTRACT
--------
`resolve_within(root, fragment)` returns a resolved path that is provably
inside `root`, or `None`. It NEVER raises for bad input, and it NEVER reports
anything about a path outside the root — callers cannot accidentally turn a
rejection into a 404-vs-403 distinction that leaks whether the target exists.

Three-valued by construction: a caller gets a path (allowed), or `None`
(rejected). "Exists" is deliberately NOT part of this answer — ask afterwards,
once containment is settled. Checking existence first is the bug this module
exists to prevent.

USAGE
-----
    from apps.infra.platform_app.services.paths import resolve_within

    target = resolve_within(project_root, request.GET.get("path", ""))
    if target is None:
        return JsonResponse({"error": "Invalid path"}, status=403)
    if not target.is_dir():                 # existence checked AFTER containment
        return JsonResponse({"error": "Not found"}, status=404)
"""

from __future__ import annotations

from pathlib import Path

__all__ = ["resolve_within"]


def resolve_within(root: Path, fragment: str | None) -> Path | None:
    """Resolve ``fragment`` under ``root``, or return ``None`` if it escapes.

    ``fragment`` is untrusted. It may be empty (meaning ``root`` itself),
    contain ``..`` segments, be absolute, or point through a symlink that
    leaves ``root``; every one of those is resolved first and rejected if the
    result is not inside ``root``.

    Returns the RESOLVED path on success, so callers use the value that was
    actually validated rather than re-joining and validating a second time.
    Returns ``None`` on rejection — never raises, and never distinguishes
    "outside the root" from "malformed", because that distinction is itself
    information about paths the caller is not allowed to learn about.
    """
    if root is None:
        return None

    text = "" if fragment is None else str(fragment).strip()

    # A leading "/" would make pathlib DISCARD the root entirely
    # (Path("/srv/proj") / "/etc/passwd" == Path("/etc/passwd")), so strip it
    # before joining. The containment check below would catch it anyway; this
    # keeps the common "/foo/bar" form working as the relative path a caller
    # plainly meant, instead of rejecting it.
    text = text.strip("/")

    # NUL is rejected outright: it terminates the string at the OS boundary,
    # so a path validated here could be truncated to a different path when it
    # reaches a syscall.
    if "\x00" in text:
        return None

    try:
        root_resolved = Path(root).resolve()
        candidate = (root_resolved / text).resolve() if text else root_resolved
    except (ValueError, OSError, RuntimeError):
        # RuntimeError: pathlib raises it on a symlink loop.
        return None

    # is_relative_to (3.9+) states the intent directly and, unlike
    # relative_to(), does not use an exception for the ordinary "no" answer.
    if not candidate.is_relative_to(root_resolved):
        return None

    return candidate
