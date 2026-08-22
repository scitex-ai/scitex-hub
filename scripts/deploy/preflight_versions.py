#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Does a version satisfy a specifier -- and if that cannot be decided, say so.

``packaging`` is used when the deploy host has it. It is not assumed: the deploy
runs on the NAS from a plain checkout, and a preflight that cannot start on the
machine that deploys is a preflight that gets deleted from the deploy path. The
fallback implements the subset of PEP 440 that hub's own pyproject actually uses
-- ``>=``, ``>``, ``<=``, ``<``, ``==`` (incl. a trailing ``.*``), ``!=`` and
``~=`` -- over release tuples with pre/post/dev ordering.

The important behaviour is the third value. ``satisfies`` returns True, False, or
raises :class:`Undecidable`. It never guesses. A version string the comparator
cannot parse produces a refusal that names the string, not a cheerful default --
because a floor that could not be evaluated and a floor that was satisfied look
identical the moment you let them.
"""

import re

try:  # pragma: no cover - depends on the host, both branches are exercised below
    from packaging.specifiers import SpecifierSet as _SpecifierSet
    from packaging.version import InvalidVersion as _InvalidVersion
    from packaging.version import Version as _Version

    BACKEND = "packaging"
except Exception:  # noqa: BLE001
    _SpecifierSet = None
    _Version = None
    _InvalidVersion = Exception
    BACKEND = "builtin"


class Undecidable(Exception):
    """The comparison could not be made. Callers must treat this as UNKNOWN."""


_RELEASE = re.compile(r"^\s*v?(\d+(?:\.\d+)*)(.*)$")
_SUFFIX = re.compile(
    r"^(?:[-_.]?(a|b|c|rc|alpha|beta|pre|preview)[-_.]?(\d*))?"
    r"(?:[-_.]?(post|rev|r)[-_.]?(\d*))?"
    r"(?:[-_.]?(dev)[-_.]?(\d*))?$"
)
_PRE_RANK = {"a": 0, "alpha": 0, "b": 1, "beta": 1, "c": 2, "rc": 2, "pre": 2, "preview": 2}


def _key(version):
    """A sortable key for ``version``, or raise :class:`Undecidable`."""
    text = str(version).strip().split("+")[0]  # local version segment is not ordered
    match = _RELEASE.match(text)
    if not match:
        raise Undecidable("cannot parse version {0!r}".format(version))
    release = tuple(int(part) for part in match.group(1).split("."))
    suffix = _SUFFIX.match(match.group(2) or "")
    if suffix is None:
        raise Undecidable("cannot parse version suffix {0!r} in {1!r}".format(match.group(2), version))
    pre_kind, pre_num, post_kind, post_num, dev_kind, dev_num = suffix.groups()
    # dev < pre < release < post, matching PEP 440's ordering closely enough for
    # the floors hub declares. Anything more exotic goes through `packaging`.
    if dev_kind:
        stage = (-2, int(dev_num or 0))
    elif pre_kind:
        stage = (-1, _PRE_RANK[pre_kind] * 1000 + int(pre_num or 0))
    elif post_kind:
        stage = (1, int(post_num or 0))
    else:
        stage = (0, 0)
    return (release, stage)


def _compare(left, right):
    """-1/0/1 over two version strings, padding release tuples to equal length."""
    (l_release, l_stage), (r_release, r_stage) = _key(left), _key(right)
    width = max(len(l_release), len(r_release))
    l_release = l_release + (0,) * (width - len(l_release))
    r_release = r_release + (0,) * (width - len(r_release))
    if l_release != r_release:
        return -1 if l_release < r_release else 1
    if l_stage != r_stage:
        return -1 if l_stage < r_stage else 1
    return 0


_CLAUSE = re.compile(r"^\s*(===|==|!=|~=|>=|<=|>|<)\s*(.+?)\s*$")


def _satisfies_builtin(version, specifier):
    for clause in specifier.split(","):
        clause = clause.strip()
        if not clause:
            continue
        match = _CLAUSE.match(clause)
        if not match:
            raise Undecidable("cannot parse specifier clause {0!r}".format(clause))
        operator, wanted = match.groups()
        if operator in ("==", "===") and wanted.endswith(".*"):
            prefix = wanted[:-2]
            if not (str(version) == prefix or str(version).startswith(prefix + ".")):
                return False
            continue
        if operator == "~=":
            if "." not in wanted:
                raise Undecidable("~= needs at least two release segments: {0!r}".format(clause))
            if _compare(version, wanted) < 0:
                return False
            prefix = wanted.rsplit(".", 1)[0]
            if not (str(version) == prefix or str(version).startswith(prefix + ".")):
                return False
            continue
        result = _compare(version, wanted)
        if operator == "==" and result != 0:
            return False
        if operator == "===" and str(version) != wanted:
            return False
        if operator == "!=" and result == 0:
            return False
        if operator == ">=" and result < 0:
            return False
        if operator == ">" and result <= 0:
            return False
        if operator == "<=" and result > 0:
            return False
        if operator == "<" and result >= 0:
            return False
    return True


def satisfies(version, specifier):
    """True/False, or raise :class:`Undecidable`. Never a silent default."""
    if not specifier or not specifier.strip():
        raise Undecidable("empty specifier")
    if _SpecifierSet is not None:
        try:
            return _SpecifierSet(specifier, prereleases=True).contains(_Version(str(version)))
        except _InvalidVersion as exc:
            raise Undecidable("invalid version {0!r}: {1}".format(version, exc))
        except Undecidable:
            raise
        except Exception as exc:  # noqa: BLE001
            raise Undecidable("invalid specifier {0!r}: {1}".format(specifier, exc))
    return _satisfies_builtin(version, specifier)

# EOF
