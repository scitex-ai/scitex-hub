#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""No compose service may declare two mounts on the same container path.

WHY THIS TEST EXISTS. Measured on scitex-hub-dev-django-1, 2026-09-06. The dev
django service mounted ``/app/staticfiles`` TWICE::

    :68      - static_volume:/app/staticfiles      # "Persistent data"
    :97      - /app/staticfiles                    # "exclude from host mount"

Docker takes the last one, so the bare entry created an ANONYMOUS volume that
shadowed ``static_volume``::

    docker volume inspect --format '{{json .Labels}}'
        -> {"com.docker.volume.anonymous": ""}

``static_volume`` was declared, mounted, overridden and read by nobody. The
consequence was not cosmetic: the Vite bundle lives under that path, so it did
not survive a recreate, and with ``SCITEX_HUB_VITE_USE_BUILD=true`` an empty
``staticfiles`` makes every page raise under DEBUG -- Django's technical 500,
settings table included, on a host reachable from the internet.

WHY A GATE AND NOT A FIX. Both lines were individually reasonable and neither
author was careless: :97's intent (keep generated files out of the host bind
mount) is legitimate, and :68 already achieved it. The conflict is invisible in
review -- the two entries are thirty lines apart in a fifty-entry list -- and
visible only by inspecting a running container. That is exactly the class of
defect a parser should own rather than a reader.

THE RULE IS NOT "no anonymous volumes". A bare ``- /app/.cache`` is the correct
way to keep a generated directory out of a host bind mount when nothing else
claims that path. The defect is only ever the COLLISION.
"""

from __future__ import annotations

import pytest

from ._compose_helpers import (
    MIN_EXPECTED_COMPOSE_FILES,
    REPO_ROOT,
    UNPARSEABLE_SERVICE,
    compose_files,
    services,
)


def mount_target(entry) -> str | None:
    """The container path a compose ``volumes:`` entry mounts onto.

    Short form is ``src:dst``, ``src:dst:opts`` or a bare ``dst`` (anonymous
    volume). Long form is a mapping carrying ``target``.
    """
    if isinstance(entry, dict):
        target = entry.get("target")
        return str(target) if target else None
    text = str(entry).strip().strip('"').strip("'")
    if not text:
        return None
    parts = text.split(":")
    if len(parts) == 1:
        return parts[0]
    return parts[1]


def services_with_volumes():
    """(file, service_name, service) for every service declaring volumes."""
    found = []
    for path in compose_files():
        for name, service in services(path):
            if name == UNPARSEABLE_SERVICE:
                # An unparseable file must go RED, not vanish from the sweep.
                found.append((path, name, service))
                continue
            if service.get("volumes"):
                found.append((path, name, service))
    return found


def duplicate_targets(service) -> dict:
    """{target: [entries]} for every container path mounted more than once."""
    seen: dict = {}
    for entry in service.get("volumes") or []:
        target = mount_target(entry)
        if target:
            seen.setdefault(target, []).append(entry)
    return {t: e for t, e in seen.items() if len(e) > 1}


# ---------------------------------------------------------------------------
# Controls -- a sweep that finds nothing passes every rule vacuously.
# ---------------------------------------------------------------------------


def test_compose_discovery_found_the_expected_files():
    """A glob matching nothing would make the whole gate pass by finding none."""
    # Arrange / Act
    count = len(compose_files())

    # Assert
    assert count >= MIN_EXPECTED_COMPOSE_FILES, (
        f"compose discovery found {count} files, below the floor of "
        f"{MIN_EXPECTED_COMPOSE_FILES}. The glob broke; this gate is not "
        "running, it is reporting clean over an empty population."
    )


def test_sweep_actually_found_services_declaring_volumes():
    """The judged population must be non-empty for the rule below to mean anything."""
    # Arrange / Act
    count = len(services_with_volumes())

    # Assert
    assert count > 0, (
        "no compose service declaring `volumes:` was found. Either the parser "
        "stopped reading them or discovery is empty -- both make this gate "
        "vacuous while it still reports green."
    )


def test_the_detector_flags_a_synthetic_duplicate():
    """POSITIVE CONTROL for the crux function.

    Every real assertion here is negative ("no duplicates"), and a detector
    that could never fire would satisfy all of them.
    """
    # Arrange -- the exact shape measured on the dev django service.
    service = {
        "volumes": [
            "static_volume:/app/staticfiles",
            "../../..:/app:cached",
            "/app/staticfiles",
        ]
    }

    # Act
    duplicates = duplicate_targets(service)

    # Assert
    assert "/app/staticfiles" in duplicates, (
        "the detector did not flag a path mounted by both a named volume and "
        "a bare anonymous entry -- the real defect it exists to catch."
    )
    assert len(duplicates["/app/staticfiles"]) == 2


def test_the_detector_clears_distinct_targets():
    """NEGATIVE CONTROL: a detector that flags everything would also pass above."""
    # Arrange
    service = {
        "volumes": [
            "static_volume:/app/staticfiles",
            "/app/.cache",
            "/app/.jsbuild",
            "../../..:/app:cached",
            {"type": "volume", "source": "x", "target": "/app/media"},
        ]
    }

    # Act / Assert
    assert duplicate_targets(service) == {}


# ---------------------------------------------------------------------------
# The rule
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "path,name,service",
    services_with_volumes(),
    ids=lambda v: (
        str(v.relative_to(REPO_ROOT)) if hasattr(v, "relative_to") else str(v)[:40]
    ),
)
def test_service_mounts_each_container_path_once(path, name, service):
    # Arrange / Act
    duplicates = duplicate_targets(service)

    # Assert
    # Repo-relative, never path.name: two compose files here are both called
    # docker-compose.override.yml, and a basename sent me to inspect the wrong
    # one until I checked. A gate's message must identify the file uniquely.
    relative = path.relative_to(REPO_ROOT)
    assert not duplicates, (
        f"{relative}: service {name!r} mounts the same container path more "
        f"than once: {duplicates}. Docker keeps only the LAST entry, so the "
        "earlier one is silently discarded -- a named volume overridden by a "
        "bare path becomes an anonymous volume that does not survive a "
        "recreate, and nothing anywhere reports the override. Delete "
        "whichever entry is redundant; if both are wanted for different "
        "reasons, they still cannot both apply."
    )
