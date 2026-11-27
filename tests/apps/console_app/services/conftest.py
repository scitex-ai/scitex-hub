"""A fake SLURM toolkit on PATH for tests of Hub launchers.

The launchers call ``sbatch``/``squeue``/``srun``/``scancel``/``sinfo`` as
real subprocesses. Rather than patching ``subprocess.run``, this fixture puts
small executables of those names first on ``PATH``. Each records its argv
(and stdin) to a JSONL log and answers like a healthy single-node cluster.
"""

from __future__ import annotations

import json
import os
import stat
import sys
from pathlib import Path

import pytest

_FAKE = r"""#!{python}
import json, os, sys
name = os.path.basename(sys.argv[0])
argv = sys.argv[1:]
stdin = "" if sys.stdin is None or sys.stdin.isatty() else sys.stdin.read()
with open(os.environ["FAKE_SLURM_LOG"], "a") as log:
    log.write(json.dumps({{"cmd": name, "argv": argv, "stdin": stdin}}) + "\n")
job_id = os.environ.get("FAKE_SLURM_JOB_ID", "4242")
if name == "sbatch":
    if os.environ.get("FAKE_SBATCH_FAIL"):
        sys.stderr.write("sbatch: error: Batch job submission failed\n")
        sys.exit(1)
    print(job_id if "--parsable" in argv else f"Submitted batch job {{job_id}}")
elif name == "squeue":
    print("RUNNING" if "--job" in argv else "")
elif name == "sinfo":
    print("node01 idle")
elif name == "srun":
    print(os.environ.get("FAKE_SRUN_STDOUT", ""))
"""

_NAMES = ("sbatch", "squeue", "srun", "scancel", "sinfo")


class FakeSlurm:
    def __init__(self, root: Path):
        self.bin = root / "fake-slurm-bin"
        self.bin.mkdir()
        self.log = root / "fake-slurm.jsonl"
        self.log.touch()
        body = _FAKE.format(python=sys.executable)
        for name in _NAMES:
            exe = self.bin / name
            exe.write_text(body)
            exe.chmod(exe.stat().st_mode | stat.S_IXUSR)
        self._saved: dict[str, str | None] = {}

    def set(self, **env: str) -> None:
        """Set environment variables until the fixture tears down."""
        for key, value in env.items():
            self._saved.setdefault(key, os.environ.get(key))
            os.environ[key] = value

    def restore(self) -> None:
        for key, value in self._saved.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

    def calls(self, cmd: str) -> list[dict]:
        rows = [json.loads(ln) for ln in self.log.read_text().splitlines() if ln]
        return [r for r in rows if r["cmd"] == cmd]


@pytest.fixture
def fake_slurm(tmp_path):
    fake = FakeSlurm(tmp_path)
    fake.set(
        PATH=f"{fake.bin}{os.pathsep}{os.environ['PATH']}",
        FAKE_SLURM_LOG=str(fake.log),
    )
    yield fake
    fake.restore()
