#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""`make status` and `make status-live` must cover the SAME sections.

They did not. `check-status.sh` ran fifteen numbered sections;
`check_status_live.sh` hand-inlined its own bash for five of them. Ten
sections existed in one surface only -- DISK AMONG THEM -- so on 2026-08-09,
when a 393G volume reached 100% with nothing alarming, one of the two commands
an admin might run to look was structurally unable to notice.

The fix is that the list is data: deployment/host-setup/checks/sections.sh is
the one registry and both orchestrators iterate it. These tests hold that
shape, because the shape is the whole fix -- a registry that one script
quietly stops using is the same bug again.

WHAT EACH TEST IS FOR
  registry_is_readable        the registry parses, and is not empty. Every
                              other test here is vacuous against an empty
                              list, so this one runs first and is the reason
                              the others can be trusted.
  every_command_exists        a section naming a path that is not there is a
                              check that silently never runs -- identical, from
                              the operator's chair, to not having the check.
  disk_section_is_registered  the specific regression that motivated this.
  orchestrators_use_registry  both scripts source it.
  no_second_section_list      neither script names section scripts directly.
                              This is the anti-duplication invariant: without
                              it, a future edit re-inlines one check and the
                              registry silently becomes advisory.

None of this needs docker, systemd or SLURM -- it reads the wiring, not the
host. That is deliberate: the wiring is what broke, and it is checkable
everywhere the suite runs.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
CHECKS_DIR = REPO / "deployment" / "host-setup" / "checks"
REGISTRY = CHECKS_DIR / "sections.sh"

ORCHESTRATORS = (
    CHECKS_DIR / "check-status.sh",
    REPO / "scripts" / "maintenance" / "check_status_live.sh",
)

#: Below this, assume the registry failed to expand rather than that hub
#: genuinely shrank its status check to a handful of sections. Chosen well
#: under the current count so a deliberate removal does not trip it.
_MIN_SECTIONS = 10

#: Matches a section-script filename in either naming style actually used
#: (check-slurm.sh, check_disk_space.sh). `sections.sh` itself is excluded by
#: the pattern requiring a `check` prefix.
_SECTION_SCRIPT_RE = re.compile(r"\bcheck[-_][A-Za-z0-9_-]+\.sh\b")


@pytest.fixture(name="sections", scope="module")
def _sections() -> list[tuple[str, str]]:
    """Expand the registry by running it, since it is bash and bash owns it.

    Reading it with a regex instead would assert that this test can parse the
    file, not that the file works -- and the orchestrators source it, so what
    matters is what bash makes of it.
    """
    script = (
        f'set -euo pipefail\n'
        f'export SECTIONS_SCRIPT_DIR="{CHECKS_DIR}"\n'
        f'export SECTIONS_PROJECT_ROOT="{REPO}"\n'
        f'source "{REGISTRY}"\n'
        f"status_sections\n"
    )
    proc = subprocess.run(
        ["bash", "-c", script], capture_output=True, text=True, timeout=60
    )
    assert proc.returncode == 0, (
        f"the section registry failed to expand (rc={proc.returncode}).\n"
        f"stderr: {proc.stderr.strip()}"
    )

    parsed: list[tuple[str, str]] = []
    for line in proc.stdout.splitlines():
        if not line.strip():
            continue
        name, _, command = line.partition("\t")
        parsed.append((name.strip(), command.strip()))
    return parsed


def test_registry_is_readable_and_not_empty(
    sections: list[tuple[str, str]],
) -> None:
    # Arrange / Act
    count = len(sections)

    # Assert — an empty expansion would make every other test here pass
    # while `make status` checked nothing at all.
    assert count >= _MIN_SECTIONS, (
        f"the section registry expanded to {count} section(s), below the "
        f"sanity floor of {_MIN_SECTIONS}. Either it failed to expand, or the "
        f"status check genuinely shrank -- both need a human to look."
    )


def test_every_registered_command_exists_and_is_executable(
    sections: list[tuple[str, str]],
) -> None:
    # Arrange
    # Act
    broken = [
        (name, command)
        for name, command in sections
        if not (Path(command).is_file() and Path(command).stat().st_mode & 0o111)
    ]

    # Assert — a section pointing at a missing or non-executable path produces
    # no output and no error, which reads exactly like a passing check.
    assert broken == [], (
        f"these registered sections name a path that is missing or not "
        f"executable, so they would silently never run: {broken}"
    )


def test_disk_section_is_registered(sections: list[tuple[str, str]]) -> None:
    # Arrange — the regression this whole file exists for.
    names = [name for name, _ in sections]

    # Act
    has_disk = any("disk" in name for name in names)

    # Assert
    assert has_disk, (
        f"no disk section in the registry, so a full volume is invisible to "
        f"both status surfaces. Registered sections: {names}"
    )


@pytest.mark.parametrize("orchestrator", ORCHESTRATORS, ids=lambda p: p.name)
def test_orchestrator_iterates_the_registry(orchestrator: Path) -> None:
    # Arrange — sourcing the file is not the contract; USING it is. A script
    # that sources sections.sh and then runs its own inlined checks would
    # satisfy a mere "sections.sh appears here" assertion while ignoring every
    # section in it, so require the call that expands the list.
    code = "\n".join(
        line for line in orchestrator.read_text().splitlines()
        if not line.lstrip().startswith("#")
    )

    # Act
    sources_registry = "sections.sh" in code
    expands_registry = "status_sections" in code

    # Assert
    assert (sources_registry, expands_registry) == (True, True), (
        f"{orchestrator.relative_to(REPO)} must both source sections.sh "
        f"(found={sources_registry}) and call status_sections "
        f"(found={expands_registry}). Anything less means it is running some "
        f"other list of checks."
    )


@pytest.mark.parametrize("orchestrator", ORCHESTRATORS, ids=lambda p: p.name)
def test_orchestrator_keeps_no_second_section_list(orchestrator: Path) -> None:
    # Arrange — comments are stripped first: these files EXPLAIN the history
    # in prose, and naming check_disk_space.sh while describing what went
    # wrong is documentation, not a second list.
    code = "\n".join(
        line for line in orchestrator.read_text().splitlines()
        if not line.lstrip().startswith("#")
    )

    # Act
    named = sorted(set(_SECTION_SCRIPT_RE.findall(code)))

    # Assert — the registry is the only place a section may be named.
    assert named == [], (
        f"{orchestrator.relative_to(REPO)} names section scripts directly: "
        f"{named}. Add sections to "
        f"deployment/host-setup/checks/sections.sh instead -- a second list "
        f"is what made the two status surfaces disagree."
    )
