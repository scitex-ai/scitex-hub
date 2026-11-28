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
# Configuration lives in a file next to the fake binaries, not in the
# environment: launchers hand SLURM an allowlisted environment, so the
# test's own variables never reach these processes.
root = os.path.dirname(os.path.dirname(os.path.abspath(sys.argv[0])))
with open(os.path.join(root, "fake-slurm-config.json")) as fh:
    cfg = json.load(fh)
with open(cfg["FAKE_SLURM_LOG"], "a") as log:
    log.write(json.dumps({{"cmd": name, "argv": argv, "stdin": stdin,
                          "env_names": sorted(os.environ)}}) + "\n")
job_id = cfg.get("FAKE_SLURM_JOB_ID", "4242")
if name == "sbatch":
    if cfg.get("FAKE_SBATCH_FAIL"):
        sys.stderr.write("sbatch: error: Batch job submission failed\n")
        sys.exit(1)
    print(job_id if "--parsable" in argv else f"Submitted batch job {{job_id}}")
elif name == "squeue":
    print("RUNNING" if "--job" in argv else "")
elif name == "sinfo":
    print("node01 idle")
elif name == "srun":
    print(cfg.get("FAKE_SRUN_STDOUT", ""))
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
        self._config_path = root / "fake-slurm-config.json"
        self._config: dict[str, str] = {}
        self._write_config()

    def _write_config(self) -> None:
        self._config_path.write_text(json.dumps(self._config))

    def set(self, **env: str) -> None:
        """Configure the fake (``FAKE_*`` keys, kept in a config file) or set
        real environment variables (anything else) until teardown."""
        for key, value in env.items():
            if key.startswith("FAKE_"):
                self._config[key] = value
                continue
            self._saved.setdefault(key, os.environ.get(key))
            os.environ[key] = value
        self._write_config()

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
