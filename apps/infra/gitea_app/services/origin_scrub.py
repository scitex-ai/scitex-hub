#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: ./apps/infra/gitea_app/services/origin_scrub.py

"""A repo's ``origin`` remote must carry NO embedded credential.

Single home for that guarantee. Previously this lived, byte-identical, in two
``git_service.py`` copies — two places to fix and one to forget, for a control
whose whole job is to not be forgotten.

SECURITY BACKGROUND (card ``sec-gitea-admin-token-plaintext-in-user-gitconfig``)
-------------------------------------------------------------------------------
An earlier ``configure_git_credentials()`` wrote ``http://<user>:<token>@host``
into ``origin``, persisting the platform Gitea ADMIN token into ``.git/config``.
That file is bind-mounted read/write into the user's Apptainer console at
``/workspace``, so any tenant — including the shared anonymous account — could
``cat /workspace/.git/config`` and recover a platform admin token. Credentials
are now supplied per-operation via ``build_gitea_auth_env`` and never written to
disk, so ``origin`` only ever needs a bare URL.
"""

import enum
import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import List

logger = logging.getLogger(__name__)


def strip_url_credentials(url: str) -> str:
    """Return ``url`` with any ``user[:password]@`` userinfo removed.

    ``http://alice:TOKEN@gitea:3000/a/b.git`` -> ``http://gitea:3000/a/b.git``
    and ``http://TOKEN@gitea:3000/a/b.git`` -> ``http://gitea:3000/a/b.git``.
    Non-``scheme://`` URLs (e.g. ``git@host:path`` SSH) are returned untouched.

    Only the AUTHORITY component is examined — an ``@`` later in the path is
    left alone, so ``http://gitea:3000/u/re@po.git`` survives intact instead
    of being mangled into ``http://po.git``.
    """
    if "://" not in url:
        return url
    scheme, rest = url.split("://", 1)
    authority, slash, path = rest.partition("/")
    if "@" in authority:
        # Last '@' wins: userinfo may legally contain an escaped '@', and this
        # matches how git/curl split the authority.
        authority = authority.rsplit("@", 1)[1]
    return f"{scheme}://{authority}{slash}{path}"


class OriginScrubStatus(enum.Enum):
    """Outcome of one :func:`sanitize_origin_url` call.

    Distinct members on purpose. The previous implementation returned a bare
    bool, collapsing "already clean", "I rewrote a poisoned origin", "there is
    no origin" and "I could not look" into two values — and the caller then
    discarded even those. A security control must be able to say WHICH of those
    happened, and "unknown" is a real answer that must not be folded into
    either pole.
    """

    ALREADY_CLEAN = "already-clean"  # origin carried no credential
    SCRUBBED = "scrubbed"  # credential found and REMOVED (verified)
    NO_ORIGIN = "no-origin"  # repo has no origin remote to scrub
    UNREADABLE = "unreadable"  # could not read .git/config — UNKNOWN, not safe
    FAILED = "failed"  # tried to scrub, could not verify it worked


@dataclass(frozen=True)
class OriginScrubResult:
    """Fixed-shape answer from :func:`sanitize_origin_url`.

    Branch on :attr:`is_safe`, which is deliberately conservative: UNREADABLE
    and FAILED are NOT safe. A repo we could not inspect is not a repo we know
    to be clean.
    """

    path: Path
    status: OriginScrubStatus
    detail: str = ""

    def __post_init__(self) -> None:
        # Validator: fail where the answer is BUILT, not three layers later.
        if not isinstance(self.status, OriginScrubStatus):
            raise TypeError(
                f"status must be OriginScrubStatus, got {self.status!r}"
            )
        if (
            self.status
            in (OriginScrubStatus.UNREADABLE, OriginScrubStatus.FAILED)
            and not self.detail
        ):
            raise ValueError(
                f"{self.status.value} result must carry a detail explaining why"
            )

    @property
    def is_safe(self) -> bool:
        """True only when origin is KNOWN to carry no credential."""
        return self.status in (
            OriginScrubStatus.ALREADY_CLEAN,
            OriginScrubStatus.SCRUBBED,
            OriginScrubStatus.NO_ORIGIN,
        )


_GIT_SECTION_RE = re.compile(r"^\s*\[(?P<body>[^\]]*)\]")
_GIT_URL_RE = re.compile(r"^(?P<lead>\s*url\s*=\s*)(?P<url>\S.*?)(?P<trail>\s*)$")


def _is_origin_section(header_body: str) -> bool:
    """True for ``[remote "origin"]`` in git's accepted spellings."""
    normalized = " ".join(header_body.split()).replace('"', "")
    return normalized == "remote origin"


def sanitize_origin_url(project_dir: Path) -> OriginScrubResult:
    """Strip any embedded credential from ``project_dir``'s ``origin`` remote.

    WHY THIS EDITS THE FILE DIRECTLY INSTEAD OF SHELLING OUT TO GIT
    ---------------------------------------------------------------
    The previous version ran ``git remote get-url`` / ``git remote set-url``.
    Measured on the running prod container 2026-07-29, EVERY such call failed::

        git remote get-url origin -> rc=128
        fatal: detected dubious ownership in repository at
               '/app/data/users/<user>/proj/<repo>'

    The container uid differs from the bind-mounted file owner, so git's
    ``safe.directory`` guard rejected every user repo. This function therefore
    returned False for every repo, and its caller discarded that — the scrub
    had NEVER RUN IN PRODUCTION while its unit test passed, because the test
    fixture repo is owned by the test user and so never met the production
    condition. Result: 6 of 46 user ``.git/config`` files still held
    credentials, 4 of them the live platform admin token.

    A remote URL lives in a plain INI file this process can already read and
    write; git's ownership guard is irrelevant to that. Removing the subprocess
    removes the whole class — a security control that shells out inherits the
    external tool's environment assumptions, and its unit test will not see
    them. This is the same technique used to contain the live incident, which
    worked precisely BECAUSE git was unusable there.

    The file is rewritten IN PLACE rather than via temp-file+rename: rename
    would create a file owned by *this* process, changing ownership of a
    tenant's file. Truncate+write preserves inode, owner and mode. The write is
    then VERIFIED by re-reading — the old code never checked whether its
    ``set-url`` succeeded and returned True regardless.

    Idempotent; a clean origin is left untouched. Takes NO credential arguments
    by design: a function that never receives the token cannot reintroduce the
    leak.

    Returns:
        :class:`OriginScrubResult`. Branch on ``.is_safe``; never assume.
    """
    project_dir = Path(project_dir)
    dot_git = project_dir / ".git"
    config_path = dot_git / "config"

    try:
        if not config_path.is_file():
            # ``.git`` as a FILE means a worktree/submodule pointing elsewhere.
            # Do not guess where — say so loudly rather than silently no-op,
            # which is exactly how the previous version hid a live leak.
            if dot_git.is_file():
                return OriginScrubResult(
                    project_dir,
                    OriginScrubStatus.UNREADABLE,
                    f"{dot_git} is a gitdir pointer (worktree/submodule); "
                    "config not resolved",
                )
            return OriginScrubResult(
                project_dir,
                OriginScrubStatus.UNREADABLE,
                f"no git config at {config_path}",
            )
        original_text = config_path.read_text(
            encoding="utf-8", errors="surrogateescape"
        )
    except OSError as exc:
        return OriginScrubResult(
            project_dir, OriginScrubStatus.UNREADABLE, f"read failed: {exc}"
        )

    in_origin = False
    found_origin_url = False
    changed = False
    out: List[str] = []

    for line in original_text.splitlines(keepends=True):
        section = _GIT_SECTION_RE.match(line)
        if section:
            in_origin = _is_origin_section(section.group("body"))
            out.append(line)
            continue

        if in_origin:
            stripped = line.rstrip("\r\n")
            url_match = _GIT_URL_RE.match(stripped)
            if url_match:
                found_origin_url = True
                raw = url_match.group("url")
                clean = strip_url_credentials(raw)
                if clean != raw:
                    eol = line[len(stripped) :]
                    line = (
                        f"{url_match.group('lead')}{clean}"
                        f"{url_match.group('trail')}{eol}"
                    )
                    changed = True
        out.append(line)

    if not found_origin_url:
        return OriginScrubResult(project_dir, OriginScrubStatus.NO_ORIGIN)
    if not changed:
        return OriginScrubResult(project_dir, OriginScrubStatus.ALREADY_CLEAN)

    new_text = "".join(out)
    try:
        # In-place truncate+write: preserves inode/owner/mode (see docstring).
        with open(
            config_path, "w", encoding="utf-8", errors="surrogateescape"
        ) as handle:
            handle.write(new_text)
    except OSError as exc:
        return OriginScrubResult(
            project_dir, OriginScrubStatus.FAILED, f"write failed: {exc}"
        )

    # VERIFY, do not assume. The old code never checked its own write.
    try:
        verify_text = config_path.read_text(
            encoding="utf-8", errors="surrogateescape"
        )
    except OSError as exc:
        return OriginScrubResult(
            project_dir, OriginScrubStatus.FAILED, f"verify re-read failed: {exc}"
        )

    if verify_text != new_text:
        return OriginScrubResult(
            project_dir,
            OriginScrubStatus.FAILED,
            "post-write re-read does not match what was written",
        )

    logger.info(
        "Sanitized origin URL (removed embedded credentials) for %s", project_dir
    )
    return OriginScrubResult(project_dir, OriginScrubStatus.SCRUBBED)
