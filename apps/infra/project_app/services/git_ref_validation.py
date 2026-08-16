#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Git reference (rev / ref / hash) validation for request-supplied values.

User-supplied git revisions reach ``git`` as BARE positional argv tokens.
Even with ``shell=False`` and a list argv, a token that BEGINS with ``-`` is
parsed by git as an OPTION, not a revision (CWE-88 argument injection). For
``git diff`` / ``git show`` an option such as ``--output=<abs-path>`` writes or
truncates an attacker-chosen file OUTSIDE the tenant project directory — a
direct violation of the "no host access / tenant isolation" mandate. Because a
git revision is placed in a position that PRECEDES the ``--`` pathspec
separator, ``--`` cannot protect it; validation and/or an option terminator
must.

Two defenses, meant to be used TOGETHER (belt and suspenders):

1. ``is_valid_git_ref`` / ``validate_git_ref`` — allowlist the value to a
   conservative single-revision character set and REJECT any leading ``-``
   (option) or ``.`` (invalid ref + ``..`` range foothold) at the request
   boundary.
2. ``END_OF_OPTIONS`` — insert git's ``--end-of-options`` sentinel (git
   >= 2.24) immediately before any user-supplied revision in the argv so git
   treats everything after it as revisions / paths, never options.
"""

from __future__ import annotations

import re

from django.core.exceptions import ValidationError

# git's option terminator: everything after it is treated as a rev / path,
# never as an option. Supported by rev-walking commands since git 2.24 (2019).
END_OF_OPTIONS = "--end-of-options"

# A single git revision. The LEADING character is restricted to
# alnum / underscore so the value can never be read as an option (leading
# ``-``) nor open a ``..`` range (leading ``.``). The body covers sha (hex),
# symbolic names (HEAD, main), ancestry (HEAD~1, HEAD^), namespaced refs
# (feature/x, refs/tags/v1) and reflog / upstream selectors (@{...}). Length is
# capped to a sane maximum.
_GIT_REF_RE = re.compile(r"^[0-9A-Za-z_][0-9A-Za-z._/@{}~^-]{0,199}$")


def is_valid_git_ref(ref: str) -> bool:
    """Return True iff ``ref`` is a syntactically safe single git revision.

    The empty string means "not supplied" to callers and is NOT a ref: it
    returns False here so a caller can distinguish "absent" from "present but
    hostile" on its own terms.
    """
    return isinstance(ref, str) and bool(_GIT_REF_RE.match(ref))


def validate_git_ref(ref: str, *, field: str = "ref") -> str:
    """Return ``ref`` unchanged when valid, else raise ``ValidationError``.

    Raising loudly (never silently dropping or coercing) keeps the failure
    visible, per the no-silent-fallback rule.
    """
    if not is_valid_git_ref(ref):
        raise ValidationError(f"Invalid git {field}: {ref!r}")
    return ref


# EOF
