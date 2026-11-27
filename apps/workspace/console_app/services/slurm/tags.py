#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Attribution tags that every Hub-launched SLURM job carries.

Each job is tagged at submit time so that accounting (``sacct``) can say
which project the usage belongs to without guessing:

    --comment=project:<project>,session:<uuid>
    --wckey=p<project>

``<project>`` is the hub project's numeric id. ``<uuid>`` is the
``WorkloadSession.session_id`` of the row the Hub writes for the launch, so
a collector can join an ``sacct`` row to that row even when the Hub never
learned the numeric job id (interactive ``srun --pty`` shells exec in a
forked child).

No project
----------
Some launches genuinely have no project (the batch-job API runs in the
user's workspace, not in a project). Those pass the explicit sentinel
``NO_PROJECT`` and are tagged ``project:none`` / ``wckey=pnone``. A tag is
never left out and ``None`` is never accepted, so a forgotten project is an
error, not an untagged job.

Validation
----------
These values land in ``#SBATCH`` directives and in argv, where SLURM parses
them and shell quoting cannot help (CWE-78; see ``script_generator``). The
project must be a positive ``int`` (``bool`` refused) and the session must be
a UUID. Anything else raises ``ValueError``.
"""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Union

# The comment/wckey value used when a launch genuinely has no project.
NO_PROJECT_TAG = "none"

SLURM_LAUNCHERS = ("sbatch", "srun", "salloc")

_PROJECT_TAG_RE = re.compile(r"\A(?:[1-9][0-9]{0,18}|none)\Z")
_COMMENT_RE = re.compile(
    r"\Aproject:(?P<project>[1-9][0-9]{0,18}|none),"
    r"session:(?P<session>[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})\Z"
)


class _NoProject:
    """Sentinel type: the launch genuinely belongs to no project."""

    _instance: Optional["_NoProject"] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __repr__(self) -> str:
        return "NO_PROJECT"


NO_PROJECT = _NoProject()

ProjectRef = Union[int, _NoProject]


def project_tag(project_id: ProjectRef) -> str:
    """Return the validated project token (``"<id>"`` or ``"none"``)."""
    if project_id is NO_PROJECT:
        return NO_PROJECT_TAG
    if type(project_id) is not int or project_id < 1:
        raise ValueError(
            "Invalid project id for SLURM tags: expected a positive int "
            f"or NO_PROJECT, got {project_id!r}"
        )
    token = str(project_id)
    if not _PROJECT_TAG_RE.match(token):
        raise ValueError(f"Invalid project id for SLURM tags: {project_id!r}")
    return token


def _session_tag(session_id: Union[str, uuid.UUID]) -> str:
    try:
        parsed = (
            session_id
            if isinstance(session_id, uuid.UUID)
            else uuid.UUID(str(session_id))
        )
    except (TypeError, ValueError, AttributeError):
        raise ValueError(f"Invalid workload session id: {session_id!r}")
    token = str(parsed)
    # uuid.UUID() also accepts braces/urn forms; only the canonical form
    # (which is all we ever emit) may reach a directive.
    if not isinstance(session_id, uuid.UUID) and str(session_id) != token:
        raise ValueError(f"Invalid workload session id: {session_id!r}")
    return token


@dataclass(frozen=True)
class SlurmTags:
    """Validated attribution tags for one SLURM launch."""

    project: str
    session_id: str
    project_id: Optional[int] = field(default=None, compare=False)

    @classmethod
    def for_project(
        cls,
        project_id: ProjectRef,
        session_id: Union[str, uuid.UUID, None] = None,
    ) -> "SlurmTags":
        """Build tags for ``project_id`` (an int, or ``NO_PROJECT``).

        ``session_id`` defaults to a fresh uuid4: one per launch.
        """
        token = project_tag(project_id)
        session = _session_tag(session_id if session_id is not None else uuid.uuid4())
        return cls(
            project=token,
            session_id=session,
            project_id=None if project_id is NO_PROJECT else project_id,
        )

    @property
    def comment(self) -> str:
        return f"project:{self.project},session:{self.session_id}"

    @property
    def wckey(self) -> str:
        return f"p{self.project}"

    def argv(self) -> List[str]:
        """Options for an ``sbatch``/``srun``/``salloc`` command line."""
        return [f"--comment={self.comment}", f"--wckey={self.wckey}"]

    def directives(self) -> str:
        """``#SBATCH`` lines for a batch script."""
        return f"#SBATCH --comment={self.comment}\n#SBATCH --wckey={self.wckey}"

    def as_record(self, user_id: Optional[int], workload: str) -> Dict[str, str]:
        """The design-format tag set stored on ``WorkloadSession.tags``."""
        return {
            "scitex.user": str(user_id) if user_id is not None else "",
            "scitex.project": self.project,
            "scitex.workload": workload,
            "scitex.session": self.session_id,
            "slurm.comment": self.comment,
            "slurm.wckey": self.wckey,
        }


def with_slurm_tags(cmd: List[str], tags: SlurmTags) -> List[str]:
    """Insert the tag options right after the launcher (argv[0])."""
    if not cmd or cmd[0] not in SLURM_LAUNCHERS:
        raise ValueError(f"Not a SLURM launcher command: {cmd[:1]!r}")
    if not isinstance(tags, SlurmTags):
        raise TypeError("tags must be a SlurmTags instance")
    return [cmd[0], *tags.argv(), *cmd[1:]]


def parse_comment(comment: str) -> Dict[str, str]:
    """Parse a Hub job comment back into ``{"project", "session"}``.

    Raises ``ValueError`` for anything the Hub did not write.
    """
    match = _COMMENT_RE.match(comment or "")
    if not match:
        raise ValueError(f"Not a SciTeX Hub job comment: {comment!r}")
    return {"project": match["project"], "session": match["session"]}


__all__ = [
    "NO_PROJECT",
    "NO_PROJECT_TAG",
    "SlurmTags",
    "parse_comment",
    "project_tag",
    "with_slurm_tags",
]


# EOF
