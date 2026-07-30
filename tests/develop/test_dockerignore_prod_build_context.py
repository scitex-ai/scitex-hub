#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""``.dockerignore`` must drop the build garbage and KEEP the live landing demos.

Two properties, in opposite directions, and the test needs both:

1. **Excluded.** The prod image shipped ~1.4 GB it never uses — 437 MiB of
   agent git worktrees under ``.worktrees/`` (measured inside the running
   container 2026-07-30; ``docker inspect`` showed no bind mount there, so it
   lives in the ``COPY --chown=scitex:scitex . .`` layer at
   ``Dockerfile.prod:389``) plus 975 MB of stale demo ``.mp4`` drift.
2. **NOT excluded.** The five LIVE landing demos are ``.mp4`` files in that
   same directory tree. ``.gitignore:122`` is ``**/*.mp4`` and they exist only
   as force-added exceptions, so the tempting one-line ``*.mp4`` /
   ``videos/`` rule would 404 the landing page and ``/demos/`` — they are
   served through ``{% static %}`` from
   ``apps/infra/public_app/views/pages_data.py`` and
   ``.../landing_partials/landing_demos.html``.

A test that only asserted (1) would PASS at its strongest when the outage is
worst: exclude everything and every exclusion assertion goes green. (2) is the
regression guard, not decoration.

Why the matcher below instead of ``"path" in dockerignore_text``
----------------------------------------------------------------
A substring check answers a question nobody asked. ``.dockerignore`` patterns
are **context-root-anchored** — the existing ``node_modules/`` rule matches
``./node_modules`` and nothing nested — which is the whole reason the nested
garbage shipped in the first place. Measured proof:
``/app/.worktrees/*/.env.example`` was PRESENT in the prod image despite the
``.env.*`` rule on line 62. So the assertion has to model what Docker actually
does, or it certifies a fix that does not fix anything.

``_DockerignoreMatcher`` is a restricted port of moby's ``patternmatcher``
(the code BuildKit uses to filter the build context): per-line reading with
``#`` comments and ``!`` re-includes, ``filepath.Clean``-ed patterns, ``*``
that does not cross ``/``, ``**`` that does, last-match-wins, and
``MatchesOrParentMatches`` so an excluded directory takes its subtree with it.
It is *restricted* on purpose: an unsupported pattern character raises instead
of being silently mis-translated, so a future exotic pattern fails this file
loudly rather than quietly weakening every assertion in it.
"""

from __future__ import annotations

import posixpath
import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
DOCKERIGNORE = REPO_ROOT / ".dockerignore"

VIDEO_DIR = "apps/infra/public_app/static/public_app/videos"

# Untracked drift in the prod build checkout; 706,773,544 B + 268,698,983 B.
STALE_VIDEOS = (
    f"{VIDEO_DIR}/orochi-demo-2026-04-09.mp4",
    f"{VIDEO_DIR}/landing/orochi-demo.mp4",
)

# Tracked, force-added past .gitignore's `**/*.mp4`, and served via {% static %}.
LIVE_LANDING_DEMOS = tuple(
    f"{VIDEO_DIR}/landing/{name}-demo.mp4"
    for name in ("console", "hub", "scholar", "visualizer", "writer")
)

# 437 MiB baked into the image layer, plus the nested-secret leak it carried.
WORKTREE_PATHS = (
    ".worktrees",
    ".worktrees/agent-deadbeef/manage.py",
    ".worktrees/agent-deadbeef/.env.example",
)

# Paths that must keep reaching the image, so "excluded" cannot be free.
CONTROL_INCLUDED_PATHS = (
    "manage.py",
    "apps/infra/public_app/views/pages_data.py",
    "deployment/docker/common/scripts/entrypoint-prod.sh",
)

# Chars this port maps to regex metacharacters rather than escaping them.
_PASSTHROUGH_CHARS = frozenset("[]")
_UNSUPPORTED_CHARS = frozenset("\\{}")


class _Pattern:
    """One ``.dockerignore`` line, compiled the way moby compiles it."""

    def __init__(self, line):
        self.exclusion = line.startswith("!")
        raw = line[1:] if self.exclusion else line
        self.cleaned = _clean(raw)
        self.regex = re.compile(_compile_pattern(self.cleaned))

    def match(self, path):
        return self.regex.match(path) is not None


def _clean(pattern):
    """``filepath.Clean`` + drop a leading ``/`` (Docker treats it as relative)."""
    cleaned = posixpath.normpath(pattern) if pattern else "."
    if len(cleaned) > 1 and cleaned.startswith("/"):
        cleaned = cleaned[1:]
    return cleaned


def _compile_pattern(pattern):
    """Translate a cleaned ``.dockerignore`` pattern into an anchored regex.

    Mirrors ``patternmatcher.Pattern.compile``: ``**`` swallows ``/`` (and eats
    a following ``/``), a lone ``*`` and ``?`` stop at ``/``, ``[`` / ``]`` pass
    through as a character class, everything else is escaped literally.
    """
    out = ["^"]
    i = 0
    length = len(pattern)
    while i < length:
        ch = pattern[i]
        if ch in _UNSUPPORTED_CHARS:
            raise ValueError(
                f"unsupported .dockerignore pattern character {ch!r} in "
                f"{pattern!r}: this restricted port would mis-translate it. "
                "Extend _compile_pattern to match moby/patternmatcher before "
                "adding such a pattern."
            )
        if ch == "*":
            if i + 1 < length and pattern[i + 1] == "*":
                i += 1
                if i + 1 < length and pattern[i + 1] == "/":
                    i += 1
                out.append(".*" if i + 1 == length else "(.*/)?")
            else:
                out.append("[^/]*")
        elif ch == "?":
            out.append("[^/]")
        elif ch in _PASSTHROUGH_CHARS:
            out.append(ch)
        else:
            out.append(re.escape(ch))
        i += 1
    out.append("$")
    return "".join(out)


class _DockerignoreMatcher:
    """Docker's build-context filter: last match wins, parents drag subtrees."""

    def __init__(self, text):
        self.patterns = [_Pattern(line) for line in _read_dockerignore(text)]

    def is_excluded(self, path):
        """``patternmatcher.MatchesOrParentMatches`` for one context-relative path."""
        path = posixpath.normpath(path)
        parent = posixpath.dirname(path)
        parent_dirs = parent.split("/") if parent not in ("", ".") else []
        matched = False
        for pattern in self.patterns:
            if pattern.exclusion != matched:
                continue
            hit = pattern.match(path)
            if not hit:
                for depth in range(len(parent_dirs)):
                    if pattern.match("/".join(parent_dirs[: depth + 1])):
                        hit = True
                        break
            if hit:
                matched = not pattern.exclusion
        return matched


def _read_dockerignore(text):
    """``dockerignore.ReadAll``: strip comments/blanks, normalise, keep ``!``."""
    lines = []
    for raw in text.splitlines():
        if raw.startswith("#"):
            continue
        pattern = raw.strip()
        if not pattern:
            continue
        invert = pattern.startswith("!")
        if invert:
            pattern = pattern[1:].strip()
        if pattern:
            pattern = _clean(pattern)
        lines.append("!" + pattern if invert else pattern)
    return lines


@pytest.fixture(scope="module")
def matcher():
    """The matcher built from the repository's real ``.dockerignore``."""
    return _DockerignoreMatcher(DOCKERIGNORE.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# The probe itself — a mis-ported matcher would make every test below vacuous
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "patterns,path,expected",
    [
        # An anchored rule is root-only. This is the bug's whole mechanism.
        (["node_modules/"], "node_modules/react/index.js", True),
        (["node_modules/"], "apps/web/node_modules/react/index.js", False),
        (["**/node_modules/"], "apps/web/node_modules/react/index.js", True),
        (["**/node_modules/"], "node_modules/react/index.js", True),
        # `*` stops at a slash; `**` does not.
        ([".env.*"], ".env.dev", True),
        ([".env.*"], "sub/.env.dev", False),
        (["**/.env*"], "a/b/.env.example", True),
        # An excluded directory takes its subtree with it.
        ([".worktrees/"], ".worktrees/x/y/z.py", True),
        # Last match wins, and `!` re-includes.
        (["*.md", "!README.md"], "README.md", False),
        (["*.md"], "README.md", True),
        # An exact path excludes exactly one file, not its siblings.
        (["dir/stale.mp4"], "dir/stale.mp4", True),
        (["dir/stale.mp4"], "dir/live.mp4", False),
    ],
)
def test_matcher_reproduces_dockerignore_semantics(patterns, path, expected):
    """Ported semantics, incl. the anchoring that let the garbage ship."""
    # Arrange
    probe = _DockerignoreMatcher("\n".join(patterns))

    # Act
    excluded = probe.is_excluded(path)

    # Assert
    assert excluded is expected, (
        f"patterns={patterns!r} vs {path!r}: got excluded={excluded}, "
        f"expected {expected}. The port no longer matches moby/patternmatcher, "
        "so every .dockerignore assertion in this file is untrustworthy."
    )


def test_matcher_rejects_patterns_it_cannot_translate():
    """No silent mis-translation: an unsupported pattern must raise."""
    # Arrange
    exotic = "a\\b"

    # Act
    build = lambda: _DockerignoreMatcher(exotic)  # noqa: E731

    # Assert
    with pytest.raises(ValueError, match="unsupported .dockerignore pattern"):
        build()


# ---------------------------------------------------------------------------
# The real .dockerignore
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("path", STALE_VIDEOS)
def test_stale_demo_videos_are_excluded_from_the_build_context(matcher, path):
    """975 MB of untracked drift must not enter the COPY . . layer."""
    # Arrange
    reason = "975 MB of stale demo video is untracked drift, not a served asset"

    # Act
    excluded = matcher.is_excluded(path)

    # Assert
    assert excluded, (
        f"{path} still reaches the prod build context ({reason}). Add the "
        "EXACT path to .dockerignore — never `*.mp4` and never `videos/`, "
        "which would 404 the five live landing demos."
    )


@pytest.mark.parametrize("path", WORKTREE_PATHS)
def test_agent_worktrees_are_excluded_from_the_build_context(matcher, path):
    """437 MiB of sibling checkouts were baked into the image layer."""
    # Arrange
    reason = "no bind mount at /app/.worktrees, so this lands in the image layer"

    # Act
    excluded = matcher.is_excluded(path)

    # Assert
    assert excluded, (
        f"{path} still reaches the prod build context ({reason}). "
        "/app/.worktrees measured 437 MiB inside the running container on "
        "2026-07-30, and a nested .env.example shipped with it because the "
        "anchored `.env.*` rule is context-root-only. Add '.worktrees/'."
    )


@pytest.mark.parametrize("path", LIVE_LANDING_DEMOS)
def test_live_landing_demo_videos_are_still_included(matcher, path):
    """The positive control — and the outage this file exists to prevent."""
    # Arrange
    served_from = "apps/infra/public_app/views/pages_data.py via {% static %}"

    # Act
    excluded = matcher.is_excluded(path)

    # Assert
    assert not excluded, (
        f"{path} is EXCLUDED from the prod build context, but it is a live "
        f"asset served from {served_from}. Under the hashed manifest storage "
        "backend a missing file breaks collectstatic/{% static %}, so the "
        "landing page and /demos/ go dark. A `*.mp4` or `videos/` rule causes "
        "exactly this — use the two exact stale paths instead."
    )


@pytest.mark.parametrize("path", CONTROL_INCLUDED_PATHS)
def test_application_source_is_still_included(matcher, path):
    """Anti-vacuity: the matcher must be able to answer 'not excluded'."""
    # Arrange
    reason = "the image cannot boot without its own source"

    # Act
    excluded = matcher.is_excluded(path)

    # Assert
    assert not excluded, (
        f"{path} is excluded from the prod build context ({reason}). Either "
        ".dockerignore has grown a far too broad rule, or this matcher answers "
        "'excluded' to everything — either way the assertions above prove "
        "nothing until it is fixed."
    )


def test_root_node_modules_stays_excluded_so_the_image_keeps_its_linux_build(
    matcher,
):
    """The anchored rule must survive: Dockerfile.prod:383-386 builds it in-image."""
    # Arrange
    host_built = "node_modules/esbuild/bin/esbuild"

    # Act
    excluded = matcher.is_excluded(host_built)

    # Assert
    assert excluded, (
        "node_modules/ is no longer excluded from the prod build context. "
        "Dockerfile.prod:383-386 npm-installs into /app/node_modules "
        "immediately before `COPY --chown=scitex:scitex . .`, so re-admitting "
        "a host-built (macOS/WSL) tree would overwrite the image's "
        "linux-built one and break the startup Vite build."
    )


# EOF
