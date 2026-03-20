"""Terminal connection pipeline status — diagnostic flowchart for failures.

Tracks each stage of the terminal connection pipeline and renders
an ASCII flowchart showing exactly where a failure occurred.

Pipeline stages:
  WebSocket → Broker → SLURM → Apptainer → Shell

Usage:
    status = PipelineStatus()
    status.pass_stage("websocket")
    status.pass_stage("broker")
    status.fail_stage("slurm", "Node is DOWN")
    print(status.render())
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

logger = logging.getLogger(__name__)


class StageState(Enum):
    PENDING = "pending"
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class Stage:
    name: str
    label: str
    state: StageState = StageState.PENDING
    detail: str = ""


# Stage order matches the terminal connection pipeline
_STAGE_DEFS = [
    ("websocket", "WebSocket"),
    ("broker", "Broker"),
    ("slurm", "SLURM"),
    ("apptainer", "Apptainer"),
    ("shell", "Shell"),
]

# ANSI escape codes for terminal rendering
_GREEN = "\x1b[0;32m"
_RED = "\x1b[1;31m"
_YELLOW = "\x1b[0;33m"
_DIM = "\x1b[0;90m"
_RESET = "\x1b[0m"
_BOLD = "\x1b[1m"

_ICONS = {
    StageState.PASSED: f"{_GREEN}✓{_RESET}",
    StageState.FAILED: f"{_RED}✗{_RESET}",
    StageState.PENDING: f"{_DIM}·{_RESET}",
    StageState.SKIPPED: f"{_DIM}-{_RESET}",
}


@dataclass
class PipelineStatus:
    """Tracks terminal connection pipeline stages for diagnostic output."""

    stages: dict[str, Stage] = field(default_factory=dict)

    def __post_init__(self):
        if not self.stages:
            self.stages = {
                key: Stage(name=key, label=label) for key, label in _STAGE_DEFS
            }

    def pass_stage(self, name: str) -> None:
        if name in self.stages:
            self.stages[name].state = StageState.PASSED

    def fail_stage(self, name: str, detail: str = "") -> None:
        if name in self.stages:
            self.stages[name].state = StageState.FAILED
            self.stages[name].detail = detail
            # Mark remaining stages as skipped
            found = False
            for key in self.stages:
                if found:
                    self.stages[key].state = StageState.SKIPPED
                if key == name:
                    found = True

    def render(self) -> str:
        """Render the pipeline as a terminal-friendly flowchart.

        Returns a multi-line string with ANSI colors, suitable for
        writing directly to a PTY terminal.
        """
        lines: list[str] = []
        lines.append("")

        # Header line: stage labels with arrows
        parts: list[str] = []
        for stage in self.stages.values():
            icon = _ICONS[stage.state]
            if stage.state == StageState.FAILED:
                parts.append(f"{_RED}{_BOLD}{stage.label}{_RESET} {icon}")
            elif stage.state == StageState.PASSED:
                parts.append(f"{stage.label} {icon}")
            else:
                parts.append(f"{_DIM}{stage.label}{_RESET} {icon}")

        lines.append(f"  {' → '.join(parts)}")

        # Detail line for the failed stage
        for stage in self.stages.values():
            if stage.state == StageState.FAILED and stage.detail:
                lines.append("")
                lines.append(f"  {_RED}Error:{_RESET} {stage.detail}")
                break

        lines.append("")
        return "\r\n".join(lines)

    def render_plain(self) -> str:
        """Render without ANSI codes (for logging)."""
        parts: list[str] = []
        plain_icons = {
            StageState.PASSED: "[OK]",
            StageState.FAILED: "[FAIL]",
            StageState.PENDING: "[..]",
            StageState.SKIPPED: "[--]",
        }
        for stage in self.stages.values():
            parts.append(f"{stage.label} {plain_icons[stage.state]}")

        result = " → ".join(parts)
        for stage in self.stages.values():
            if stage.state == StageState.FAILED and stage.detail:
                result += f" | Error: {stage.detail}"
                break
        return result

    @property
    def failed_stage(self) -> Optional[str]:
        """Return the name of the failed stage, or None."""
        for stage in self.stages.values():
            if stage.state == StageState.FAILED:
                return stage.name
        return None


# EOF
