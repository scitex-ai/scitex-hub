#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: src/scitex_hub/_config/_local_state_fallback.py
"""``local_state`` resolver with a vendored fallback (issue #249).

The Apptainer prod sandbox ships ``scitex`` / ``scitex_cloud`` /
``scitex_container`` but does **not** currently ship the standalone
``scitex_config`` package. Every ``scitex_hub`` call site that needs
``scitex_config._ecosystem.local_state`` should import it from here
instead of importing ``scitex_config`` directly, so a missing
``scitex_config`` degrades gracefully instead of raising
``ModuleNotFoundError`` at import time.

Behaviour:

- If ``scitex_config`` is installed (dev boxes, CI, and — once
  issue #249's Path A lands — the prod sandbox too), the real
  ``scitex_config._ecosystem.local_state`` is used untouched.
- Otherwise, a vendored re-implementation with the *identical*
  ``path()`` / ``runtime_path()`` / ``user_path()`` contract is used
  (same ``$SCITEX_DIR`` default, same project-scope git-root walk,
  same ``runtime/`` seed files) so callers see no behavioural
  difference — only a real package is preferred over a vendored copy
  when both are present.

This intentionally does NOT return ``None`` on missing paths (unlike
a bare try/except stub) — every ``scitex_hub`` call site treats the
return value as a concrete ``Path``, so a stub that hands back
``None`` would just move the crash from import-time to first-use.
"""

from __future__ import annotations

try:
    from scitex_config._ecosystem import local_state  # type: ignore[import-not-found]
except ImportError:  # pragma: no cover - only exercised when scitex_config is absent
    import os
    from pathlib import Path

    class _LocalStateFallback:
        """Vendored copy of ``scitex_config._ecosystem._local_state``.

        Kept in lockstep with the upstream module's contract; see that
        module's docstring for the full layout spec. Do not add
        behaviour here that the real package doesn't have — this must
        stay a drop-in.
        """

        @staticmethod
        def user_root() -> "Path":
            return Path(os.environ.get("SCITEX_DIR", str(Path.home() / ".scitex")))

        @classmethod
        def find_project_scope(cls, pkg_short: str, start: "Path | None" = None) -> "Path | None":
            if start is None:
                start = Path.cwd()
            start = start.resolve()
            for candidate in [start, *start.parents]:
                if (candidate / ".git").exists():
                    scope = candidate / ".scitex" / pkg_short
                    return scope if scope.is_dir() else None
            return None

        @classmethod
        def path(cls, pkg_short: str, *parts: str) -> "Path":
            project = cls.find_project_scope(pkg_short)
            if project is not None:
                candidate = project.joinpath(*parts) if parts else project
                if candidate.exists():
                    return candidate
            root = cls.user_root() / pkg_short
            return root.joinpath(*parts) if parts else root

        @classmethod
        def runtime_path(cls, pkg_short: str, *parts: str) -> "Path":
            project = cls.find_project_scope(pkg_short)
            if project is not None:
                runtime_dir = project / "runtime"
            else:
                runtime_dir = cls.user_root() / pkg_short / "runtime"
            runtime_dir.mkdir(parents=True, exist_ok=True)
            gitkeep = runtime_dir / ".gitkeep"
            if not gitkeep.exists():
                gitkeep.write_text("")
            readme = runtime_dir / "README.md"
            if not readme.exists():
                readme.write_text(
                    "# `runtime/`\n"
                    "\n"
                    "Per-host, per-run state. Everything here is regenerable from "
                    "config + source; never commit anything except this README "
                    "and the sibling `.gitkeep`.\n"
                )
            return runtime_dir.joinpath(*parts) if parts else runtime_dir

        @classmethod
        def user_path(cls, pkg_short: str, *parts: str) -> "Path":
            base = cls.user_root() / pkg_short
            return base.joinpath(*parts) if parts else base

    local_state = _LocalStateFallback()

__all__ = ["local_state"]

# EOF
