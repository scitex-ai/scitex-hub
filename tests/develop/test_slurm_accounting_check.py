"""SLURM accounting gate: prove the check FAILS when jobs would not be metered.

WHAT WENT WRONG (2026-10-02 .. 2026-11-26, SciTeX cluster, scitex-compute-01)
slurmctld and slurmdbd lost a boot race, exited, and stayed ``failed`` for 8
weeks: the stock units have no ``Restart=``. sacct recorded nothing, so no job
on the cluster could be metered or billed -- and ``check-slurm.sh`` exited 0
the whole time, because every one of its findings was a print, never an exit.

WHY THIS GATE IS SHAPED THIS WAY ("a gate that cannot fail is not a gate").
CI has no SLURM, so every SLURM command the check calls is a SYNTHETIC stub on
``PATH`` (scontrol, sacctmgr, sacct, sdiag, sinfo, systemctl, logger), driven
by ``FAKE_SLURM_MODE``. The real script, the real parsing, the real exit code.
The healthy case is only the control proving that each failure fails *because
of* the injected fault.

    healthy         -> exit 0
    dbd_down        -> slurmdbd inactive + sacctmgr/sacct refuse   -> exit 1
    no_job_comment  -> --comment (the project tag) would be dropped -> exit 1
    no_wckey        -> --wckey would be dropped                     -> exit 1
    no_gpu_tres     -> cluster has GPUs, GPU time unmetered         -> exit 1
    filetxt_storage -> accounting not going to slurmdbd             -> exit 1
    dbd_backlog     -> records queued, not reaching the DB          -> exit 1
    ctld_down       -> controller does not answer                   -> exit 1

The restart-safe drop-ins that prevent the incident are pinned statically
below: each must restart on failure and never give up (StartLimitIntervalSec=0).

No Docker, no SLURM and no secrets required, so this runs in the headless
pytest matrix.
"""

import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
HOST_SETUP = REPO_ROOT / "deployment" / "host-setup"
CHECK_SH = HOST_SETUP / "checks" / "check-slurm-accounting.sh"
SYSTEMD_DIR = HOST_SETUP / "systemd"
CLUSTER_ETC = REPO_ROOT / "deployment" / "slurm" / "cluster" / "etc"

# One stub body serves every SLURM command; it dispatches on its own name.
FAKE_SLURM = r"""#!/bin/bash
mode="${FAKE_SLURM_MODE:?FAKE_SLURM_MODE must be set}"
cmd="$(basename "$0")"

store_type="accounting_storage/slurmdbd"
store_flags="job_comment"
wckey="Yes"
tres="cpu,mem,energy,node,billing,fs/disk,vmem,pages,gres/gpu"
dbd_queue=0
case "$mode" in
    no_job_comment)  store_flags="(null)" ;;
    no_wckey)        wckey="No" ;;
    no_gpu_tres)     tres="cpu,mem,energy,node,billing,fs/disk,vmem,pages" ;;
    filetxt_storage) store_type="accounting_storage/none" ;;
    dbd_backlog)     dbd_queue=8000 ;;
esac

case "$cmd" in
    systemctl)
        # `systemctl cat slurmdbd.service` -> present; `is-active <unit>`.
        if [ "$1" = "cat" ]; then exit 0; fi
        if [ "$1" = "is-active" ]; then
            unit="${!#}"
            if [ "$mode" = "dbd_down" ] && [ "$unit" = "slurmdbd" ]; then
                [ "$2" = "--quiet" ] || echo "failed"; exit 3
            fi
            [ "$2" = "--quiet" ] || echo "active"; exit 0
        fi
        exit 0 ;;
    scontrol)
        if [ "$1" = "ping" ]; then
            [ "$mode" = "ctld_down" ] && { echo "Slurmctld(primary) at c01 is DOWN"; exit 1; }
            echo "Slurmctld(primary) at c01 is UP"; exit 0
        fi
        [ "$mode" = "ctld_down" ] && exit 1
        cat <<EOF
Configuration data as of 2026-11-27T00:00:00
AccountingStorageTRES   = $tres
AccountingStorageType   = $store_type
AccountingStoreFlags    = $store_flags
ClusterName             = scitex
JobAcctGatherType       = jobacct_gather/cgroup
TrackWCKey              = $wckey
EOF
        exit 0 ;;
    sacctmgr)
        [ "$mode" = "dbd_down" ] && { echo "sacctmgr: error: Connection refused" >&2; exit 1; }
        echo "scitex"; exit 0 ;;
    sacct)
        [ "$mode" = "dbd_down" ] && { echo "sacct: error: Connection refused" >&2; exit 1; }
        echo "30"; exit 0 ;;
    sdiag)
        echo "DBD Agent queue size: $dbd_queue"; exit 0 ;;
    sinfo)
        echo "gpu:gtx1070:1"; exit 0 ;;
    logger)
        exit 0 ;;
esac
echo "fake slurm: unknown command $cmd" >&2
exit 64
"""

ANSI = re.compile(r"\x1b\[[0-9;]*m")
FAKE_COMMANDS = (
    "systemctl",
    "scontrol",
    "sacctmgr",
    "sacct",
    "sdiag",
    "sinfo",
    "logger",
)


@pytest.fixture(name="fake_bin")
def _fake_bin(tmp_path):
    d = tmp_path / "fake-slurm-bin"
    d.mkdir()
    for name in FAKE_COMMANDS:
        p = d / name
        p.write_text(FAKE_SLURM)
        p.chmod(0o755)
    return d


def _run_check(fake_bin: Path, mode: str) -> tuple[str, int]:
    env = {
        "PATH": f"{fake_bin}:/usr/bin:/bin",
        "FAKE_SLURM_MODE": mode,
        "HOME": os.environ.get("HOME", "/tmp"),
    }
    proc = subprocess.run(
        ["bash", str(CHECK_SH)],
        capture_output=True,
        text=True,
        env=env,
        timeout=60,
    )
    return ANSI.sub("", proc.stdout + proc.stderr), proc.returncode


BROKEN_MODES = [
    ("dbd_down", "slurmdbd is failed"),
    ("no_job_comment", "lacks job_comment"),
    ("no_wckey", "TrackWCKey is 'No'"),
    ("no_gpu_tres", "lacks gres/gpu"),
    ("filetxt_storage", "expected accounting_storage/slurmdbd"),
    ("dbd_backlog", "DBD agent queue is 8000"),
    ("ctld_down", "controller does not answer"),
]
BROKEN_IDS = [mode for mode, _ in BROKEN_MODES]


def test_healthy_cluster_exits_zero(fake_bin):
    # Arrange
    mode = "healthy"

    # Act
    _, rc = _run_check(fake_bin, mode)

    # Assert
    assert rc == 0


def test_healthy_cluster_reports_no_failure(fake_bin):
    # Arrange
    mode = "healthy"

    # Act
    out, _ = _run_check(fake_bin, mode)

    # Assert
    assert "[FAIL]" not in out, out


@pytest.mark.parametrize(("mode", "reason"), BROKEN_MODES, ids=BROKEN_IDS)
def test_broken_accounting_exits_one(fake_bin, mode, reason):
    # Arrange
    label = f"{mode} ({reason})"

    # Act
    out, rc = _run_check(fake_bin, mode)

    # Assert
    assert rc == 1, f"{label}: expected exit 1, got {rc}\n{out}"


@pytest.mark.parametrize(("mode", "reason"), BROKEN_MODES, ids=BROKEN_IDS)
def test_broken_accounting_names_the_reason(fake_bin, mode, reason):
    # Arrange
    expected = reason

    # Act
    out, _ = _run_check(fake_bin, mode)

    # Assert — the failed unit must say WHY, not only that it failed.
    assert expected in out, out


@pytest.mark.parametrize(("mode", "reason"), BROKEN_MODES, ids=BROKEN_IDS)
def test_broken_accounting_prints_the_banner(fake_bin, mode, reason):
    # Arrange
    label = f"{mode} ({reason})"

    # Act
    out, _ = _run_check(fake_bin, mode)

    # Assert
    assert "SLURM ACCOUNTING BROKEN" in out, f"{label}\n{out}"


def test_missing_slurm_tools_fail_not_pass(tmp_path):
    # Arrange — a node with no SLURM client at all must not read as healthy.
    # PATH holds only the generic tools the script uses, so no real sacct on
    # the test machine can leak in.
    for tool in ("hostname", "grep", "awk", "logger", "timeout"):
        real = shutil.which(tool)
        if real:
            (tmp_path / tool).symlink_to(real)
    env = {"PATH": str(tmp_path), "HOME": str(tmp_path)}

    # Act
    proc = subprocess.run(
        [shutil.which("bash"), str(CHECK_SH)],
        capture_output=True,
        text=True,
        env=env,
        timeout=60,
    )

    # Assert
    assert proc.returncode == 1, proc.stdout + proc.stderr


RESILIENT_UNITS = ("mariadb", "munge", "slurmdbd", "slurmctld", "slurmd")


def _section(text: str, name: str) -> str:
    m = re.search(rf"^\[{name}\]\n(.*?)(?=^\[|\Z)", text, re.S | re.M)
    return m.group(1) if m else ""


@pytest.mark.parametrize("unit", RESILIENT_UNITS)
def test_dropin_restarts_on_failure(unit):
    # Arrange — Restart= is honoured only in [Service]; elsewhere systemd
    # drops it with a warning and the unit still dies on its first fatal.
    text = (SYSTEMD_DIR / f"{unit}-resilience.conf").read_text()

    # Act
    service = _section(text, "Service")

    # Assert
    assert re.search(r"^Restart=on-failure$", service, re.M), text


@pytest.mark.parametrize("unit", RESILIENT_UNITS)
def test_dropin_never_gives_up_restarting(unit):
    # Arrange — StartLimitIntervalSec= belongs in [Unit].
    text = (SYSTEMD_DIR / f"{unit}-resilience.conf").read_text()

    # Act
    unit_section = _section(text, "Unit")

    # Assert
    assert re.search(r"^StartLimitIntervalSec=0$", unit_section, re.M), text


def test_installer_covers_every_dropin():
    # Arrange
    installer = (SYSTEMD_DIR / "install-slurm-resilience.sh").read_text()

    # Act
    m = re.search(r"^UNITS=\(([^)]*)\)", installer, re.M)
    units = sorted(m.group(1).split()) if m else []

    # Assert
    assert units == sorted(RESILIENT_UNITS)


def _canonical_keys() -> dict[str, str]:
    conf = (CLUSTER_ETC / "slurm.conf").read_text()
    pairs = (
        line.split("=", 1)
        for line in conf.splitlines()
        if "=" in line and not line.lstrip().startswith("#")
    )
    return {k: v for k, v in pairs if " " not in k}


@pytest.mark.parametrize(
    ("key", "needle"),
    [
        ("AccountingStorageType", "accounting_storage/slurmdbd"),
        ("JobAcctGatherType", "jobacct_gather/cgroup"),
        ("AccountingStoreFlags", "job_comment"),
        ("TrackWCKey", "yes"),
        ("AccountingStorageTRES", "gres/gpu"),
    ],
)
def test_canonical_slurm_conf_keeps_metering_key(key, needle):
    # Arrange
    keys = _canonical_keys()

    # Act
    value = keys.get(key, "").lower()

    # Assert
    assert needle in value, f"{key}={value!r}"


def test_slurmdbd_template_carries_only_the_password_placeholder():
    # Arrange
    text = (CLUSTER_ETC / "slurmdbd.conf.template").read_text()

    # Act
    passes = re.findall(r"^StoragePass=(.*)$", text, re.M)

    # Assert
    assert passes == ["__SLURMDBD_STORAGE_PASS__"], passes


def test_live_slurmdbd_conf_is_never_committed():
    # Arrange
    live = CLUSTER_ETC / "slurmdbd.conf"

    # Act
    exists = live.exists()

    # Assert
    assert not exists


@pytest.mark.parametrize(
    "script",
    [
        "checks/check-slurm-accounting.sh",
        "systemd/install-slurm-resilience.sh",
        "systemd/install-slurm-accounting-check.sh",
    ],
)
def test_scripts_are_executable_in_git(script):
    # Arrange — the index, not the working tree, is what a fresh checkout gets.
    path = HOST_SETUP / script

    # Act
    proc = subprocess.run(
        ["git", "-C", str(REPO_ROOT), "ls-files", "-s", "--", str(path)],
        capture_output=True,
        text=True,
        timeout=60,
    )
    mode = proc.stdout.split(" ", 1)[0] if proc.stdout else ""

    # Assert
    assert mode == "100755", f"{script} is {mode or 'untracked'} in git"
