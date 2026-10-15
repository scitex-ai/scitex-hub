"""Fail-closed POSIX identity checks for ``scitex-hub dev``."""

from __future__ import annotations

import grp
import os
import pwd
from pathlib import Path
from typing import Any

UID_MIN_DEFAULT = 20_000
UID_MAX_DEFAULT = 59_999
_UID_DOMAIN_MAX = (1 << 32) - 1


def _check(name: str, ok: bool, observed: Any, expected: str) -> dict[str, Any]:
    return {
        "name": name,
        "ok": bool(ok),
        "observed": observed,
        "expected": expected,
    }


def _ranges_overlap(first: tuple[int, int], second: tuple[int, int]) -> bool:
    return max(first[0], second[0]) <= min(first[1], second[1])


def _binding_mismatches(
    actual: dict[str, int], expected: dict[str, int]
) -> list[dict[str, Any]]:
    mismatches = []
    actual_by_id = {value: name for name, value in actual.items()}
    for name, expected_id in sorted(expected.items()):
        actual_id = actual.get(name)
        occupying_name = actual_by_id.get(expected_id)
        if actual_id != expected_id or occupying_name != name:
            mismatches.append(
                {
                    "name": name,
                    "expected_id": expected_id,
                    "actual_id": actual_id,
                    "occupying_name": occupying_name,
                }
            )
    return mismatches


def build_identity_report(
    *,
    passwd_users: dict[str, int],
    groups: dict[str, int],
    expected_users: dict[str, int],
    expected_groups: dict[str, int],
    authority_errors: list[str],
    subuid_ranges: list[tuple[int, int]],
    subgid_ranges: list[tuple[int, int]],
    subuid_errors: list[str],
    subgid_errors: list[str],
    uid_min: int = UID_MIN_DEFAULT,
    uid_max: int = UID_MAX_DEFAULT,
) -> dict[str, Any]:
    """Build the verdict from complete name-to-ID bindings and host sources."""
    managed = (uid_min, uid_max)
    subuid_conflicts = [
        {"start": start, "count": count}
        for start, count in subuid_ranges
        if _ranges_overlap(managed, (start, start + count - 1))
    ]
    subgid_conflicts = [
        {"start": start, "count": count}
        for start, count in subgid_ranges
        if _ranges_overlap(managed, (start, start + count - 1))
    ]
    uid_collisions = sorted(
        (
            {"name": name, "uid": uid}
            for name, uid in passwd_users.items()
            if uid_min <= uid <= uid_max and expected_users.get(name) != uid
        ),
        key=lambda item: (item["uid"], item["name"]),
    )
    gid_collisions = sorted(
        ({"name": name, "gid": gid} for name, gid in groups.items()
         if uid_min <= gid <= uid_max and expected_groups.get(name) != gid),
        key=lambda item: (item["gid"], item["name"]),
    )
    user_binding_errors = _binding_mismatches(passwd_users, expected_users)
    group_binding_errors = _binding_mismatches(groups, expected_groups)
    expected_uid_outside = sorted(
        (
            {"name": name, "uid": uid}
            for name, uid in expected_users.items()
            if not uid_min <= uid <= uid_max
        ),
        key=lambda item: (item["uid"], item["name"]),
    )
    expected_gid_outside = sorted(
        (
            {"name": name, "gid": gid}
            for name, gid in expected_groups.items()
            if not uid_min <= gid <= uid_max
        ),
        key=lambda item: (item["gid"], item["name"]),
    )
    checks = [
        _check(
            "valid_range",
            0 < uid_min <= uid_max < 65_534,
            [uid_min, uid_max],
            "same bounded range enforced by ComputeIdentity allocation",
        ),
        _check(
            "authority_source",
            not authority_errors,
            authority_errors,
            "authoritative ComputeIdentity name/UID/GID mappings loaded",
        ),
        _check(
            "expected_uid_range",
            not expected_uid_outside,
            expected_uid_outside,
            "every authoritative UID is inside the managed range",
        ),
        _check(
            "expected_gid_range",
            not expected_gid_outside,
            expected_gid_outside,
            "every authoritative GID is inside the managed range",
        ),
        _check(
            "subuid_source",
            not subuid_errors,
            subuid_errors,
            "readable, well-formed /etc/subuid with positive counts",
        ),
        _check(
            "subgid_source",
            not subgid_errors,
            subgid_errors,
            "readable, well-formed /etc/subgid with positive counts",
        ),
        _check(
            "subuid_overlap",
            not subuid_conflicts,
            subuid_conflicts,
            "no overlap with subordinate UID ranges",
        ),
        _check(
            "subgid_overlap",
            not subgid_conflicts,
            subgid_conflicts,
            "no overlap with subordinate GID ranges",
        ),
        _check(
            "uid_collisions",
            not uid_collisions,
            uid_collisions,
            "no unregistered account occupies the managed UID range",
        ),
        _check(
            "gid_collisions",
            not gid_collisions,
            gid_collisions,
            "no unregistered group occupies the managed GID range",
        ),
        _check(
            "user_bindings",
            not user_binding_errors,
            user_binding_errors,
            "every expected POSIX username maps to its exact ComputeIdentity UID",
        ),
        _check(
            "group_bindings",
            not group_binding_errors,
            group_binding_errors,
            "every expected POSIX group maps to its exact ComputeIdentity GID",
        ),
    ]
    return {
        "schema_version": 1,
        "operation": "dev.identity.validate",
        "mutating": False,
        "uid_range": {"min": uid_min, "max": uid_max},
        "ready": all(item["ok"] for item in checks),
        "checks": checks,
    }


def _read_subid_ranges(path: Path) -> tuple[list[tuple[int, int]], list[str]]:
    if not path.exists():
        return [], [f"missing: {path}"]
    if not path.is_file():
        return [], [f"not a regular file: {path}"]
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError) as exc:
        return [], [f"unreadable: {path}: {type(exc).__name__}"]

    ranges: list[tuple[int, int]] = []
    errors: list[str] = []
    for line_number, line in enumerate(lines, 1):
        if not line.strip():
            continue
        parts = line.split(":")
        if len(parts) != 3:
            errors.append(f"line {line_number}: expected name:start:count")
            continue
        owner = parts[0]
        if not owner or owner.strip() != owner or any(ch.isspace() for ch in owner):
            errors.append(f"line {line_number}: invalid empty/whitespace owner")
            continue
        try:
            start = int(parts[1])
            count = int(parts[2])
        except ValueError:
            errors.append(f"line {line_number}: non-integer start/count")
            continue
        if start < 0 or count <= 0:
            errors.append(f"line {line_number}: negative start or non-positive count")
            continue
        if start > _UID_DOMAIN_MAX or start + count - 1 > _UID_DOMAIN_MAX:
            errors.append(f"line {line_number}: range exceeds 32-bit UID domain")
            continue
        ranges.append((start, count))
    return ranges, errors


def _identity_authority() -> tuple[dict[str, int], dict[str, int], list[str]]:
    """Load typed ComputeIdentity mappings once the owner API is available."""
    return {}, {}, ["ComputeIdentity authority adapter is not configured"]


def collect_identity_report() -> dict[str, Any]:
    subuid_ranges, subuid_errors = _read_subid_ranges(Path("/etc/subuid"))
    subgid_ranges, subgid_errors = _read_subid_ranges(Path("/etc/subgid"))
    expected_users, expected_groups, authority_errors = _identity_authority()
    try:
        uid_min = int(os.environ.get("SCITEX_HUB_COMPUTE_UID_BASE", UID_MIN_DEFAULT))
        uid_max = int(os.environ.get("SCITEX_HUB_COMPUTE_UID_MAX", UID_MAX_DEFAULT))
    except ValueError:
        uid_min, uid_max = UID_MIN_DEFAULT, UID_MAX_DEFAULT
        authority_errors.append("compute UID range environment is not integer-valued")
    return build_identity_report(
        passwd_users={entry.pw_name: entry.pw_uid for entry in pwd.getpwall()},
        groups={entry.gr_name: entry.gr_gid for entry in grp.getgrall()},
        expected_users=expected_users,
        expected_groups=expected_groups,
        authority_errors=authority_errors,
        subuid_ranges=subuid_ranges,
        subgid_ranges=subgid_ranges,
        subuid_errors=subuid_errors,
        subgid_errors=subgid_errors,
        uid_min=uid_min,
        uid_max=uid_max,
    )
