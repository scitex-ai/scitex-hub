"""Disk & inode alarm gate: prove the alarm fires, by injecting the failure.

WHAT WENT WRONG (2026-08-09, measured on scitex-compute-04)
A 393G volume reached 100% full — zero bytes free, 92% of inodes consumed — and
NOTHING alarmed. The first notice was ``stat: write error: No space left on
device`` raised inside an unrelated task, by which point the fleet's a2a bus was
already returning HTTP 500 with no explanation. ``make status`` had no disk
metric at all: the closest thing in the tree was ``check-services.sh`` printing
how BIG the OpenAlex DB file is, which would have said ``[OK]`` at 100% full.

WHY THIS GATE IS SHAPED THIS WAY (constitution §2, "a gate that cannot fail is
not a gate"). This card is *about* a condition that never announced itself, so a
test that only ever saw a healthy disk would reproduce the exact defect it is
meant to prevent. Every threshold here is therefore driven by SYNTHETIC ``df``
output injected on ``PATH`` — the real script, the real parsing, the real
arithmetic, fed a disk that is actually full. The healthy case exists only as
the control that proves the alarming cases alarm *because of* the injected
condition rather than ambiently.

The five injected conditions, all end-to-end through the shipped script:

    healthy        -> [OK]                                     exit 0
    9% free bytes  -> [WARN]                                   exit 2
    1% free bytes  -> [FAIL]                                   exit 1
    92% inodes     -> [WARN] inodes while bytes stay [OK]      exit 2
    df errors      -> [UNKNOWN], never [OK]                    exit 2

The fourth is the incident's real shape, and the reason bytes and inodes are
reported as separate independently-triggering lines: inode exhaustion fails
writes while bytes are still plentiful, so a bytes-only check would have called
that volume healthy right up to the failure.

No Docker and no secrets required, so this runs in the headless pytest matrix.
"""

import os
import re
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
CHECK_SH = REPO_ROOT / "scripts" / "maintenance" / "check_disk_space.sh"
STATUS_SH = REPO_ROOT / "deployment" / "host-setup" / "checks" / "check-status.sh"

# Synthetic df. One fake serves every case; FAKE_DF_MODE picks the disk.
# Columns are the POSIX `df -P` layout the script parses:
#   bytes : Filesystem 1024-blocks Used Available Capacity Mounted-on
#   inodes: Filesystem Inodes IUsed IFree IUse% Mounted-on
FAKE_DF = r"""#!/bin/bash
mode="${FAKE_DF_MODE:?FAKE_DF_MODE must be set}"

want_inodes=0
for arg in "$@"; do
    [ "$arg" = "-i" ] && want_inodes=1
done

# 412316860 KiB total == 393G, the size of the volume that filled on 2026-08-09.
BYTES_HEALTHY="/dev/fake 412316860 138804396 273512464  34% /fake"
BYTES_9PCT="/dev/fake 412316860 375206860  37110000  91% /fake"
BYTES_1PCT="/dev/fake 412316860 408191860   4125000  99% /fake"
INODES_HEALTHY="/dev/fake 26214400  1981572 24232828   8% /fake"
INODES_92PCT="/dev/fake 26214400 24117248  2097152  92% /fake"

case "$mode" in
    healthy)     bytes="$BYTES_HEALTHY"; inodes="$INODES_HEALTHY" ;;
    warn_bytes)  bytes="$BYTES_9PCT";    inodes="$INODES_HEALTHY" ;;
    crit_bytes)  bytes="$BYTES_1PCT";    inodes="$INODES_HEALTHY" ;;
    warn_inodes) bytes="$BYTES_HEALTHY"; inodes="$INODES_92PCT" ;;
    df_error)
        # What df actually did during the incident: errored while measuring.
        echo "df: cannot read table of mounted file systems: Input/output error" >&2
        exit 1
        ;;
    *)
        echo "fake df: unknown FAKE_DF_MODE=$mode" >&2
        exit 64
        ;;
esac

if [ "$want_inodes" -eq 1 ]; then
    echo "Filesystem      Inodes   IUsed   IFree IUse% Mounted on"
    echo "$inodes"
else
    echo "Filesystem     1024-blocks      Used Available Capacity Mounted on"
    echo "$bytes"
fi
"""

ANSI = re.compile(r"\x1b\[[0-9;]*m")
ALARM_TOKENS = ("[WARN]", "[FAIL]", "[UNKNOWN]")


def _run_check(fake_df_dir, mode, home=None):
    """Run the shipped check against a synthetic disk. Returns (stdout, exit code).

    ``HOME`` defaults to the repo root so repo and home always resolve to a
    single filesystem, making the row count deterministic on any host.
    """
    env = dict(os.environ)
    env["PATH"] = f"{fake_df_dir}{os.pathsep}{env['PATH']}"
    env["FAKE_DF_MODE"] = mode
    env["HOME"] = home if home is not None else str(REPO_ROOT)
    proc = subprocess.run(
        ["bash", str(CHECK_SH)],
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )
    return ANSI.sub("", proc.stdout), proc.returncode


def _metric_lines(out, metric):
    """The report lines for one metric, e.g. every ``bytes`` row."""
    return [ln for ln in out.splitlines() if f" {metric} " in ln and "[" in ln]


@pytest.fixture(scope="module")
def fake_df_dir(tmp_path_factory):
    """A directory holding the synthetic df, prepended to PATH by _run_check."""
    d = tmp_path_factory.mktemp("fake-bin")
    df = d / "df"
    df.write_text(FAKE_DF, encoding="utf-8")
    df.chmod(0o755)
    return d


@pytest.fixture(scope="module")
def healthy(fake_df_dir):
    return _run_check(fake_df_dir, "healthy")


@pytest.fixture(scope="module")
def nine_pct_free(fake_df_dir):
    return _run_check(fake_df_dir, "warn_bytes")


@pytest.fixture(scope="module")
def one_pct_free(fake_df_dir):
    return _run_check(fake_df_dir, "crit_bytes")


@pytest.fixture(scope="module")
def inodes_92_pct_used(fake_df_dir):
    return _run_check(fake_df_dir, "warn_inodes")


@pytest.fixture(scope="module")
def df_errors_while_measuring(fake_df_dir):
    return _run_check(fake_df_dir, "df_error")


# ── Case 1: healthy — the control ──────────────────────────


def test_healthy_disk_exits_zero(healthy):
    # Arrange
    out, rc = healthy
    # Act
    observed = rc
    # Assert
    assert observed == 0, out


def test_healthy_disk_reports_ok(healthy):
    # Arrange
    out, _ = healthy
    # Act
    ok_lines = [ln for ln in out.splitlines() if "[OK]" in ln]
    # Assert
    assert len(ok_lines) == 2, out


def test_healthy_disk_raises_no_alarm(healthy):
    """The control must be quiet, or every alarming case below proves nothing."""
    # Arrange
    out, _ = healthy
    # Act
    fired = [token for token in ALARM_TOKENS if token in out]
    # Assert
    assert fired == [], out


# ── Case 2: 9% free bytes -> WARN ──────────────────────────


def test_nine_percent_free_exits_two(nine_pct_free):
    # Arrange
    out, rc = nine_pct_free
    # Act
    observed = rc
    # Assert
    assert observed == 2, out


def test_nine_percent_free_warns_on_bytes(nine_pct_free):
    # Arrange
    out, _ = nine_pct_free
    # Act
    byte_lines = _metric_lines(out, "bytes")
    # Assert
    assert all("[WARN]" in ln for ln in byte_lines) and byte_lines, out


def test_nine_percent_free_prints_the_measured_percentage(nine_pct_free):
    # Arrange
    out, _ = nine_pct_free
    # Act
    printed = "9.0% free" in out
    # Assert
    assert printed, out


def test_bytes_warning_names_the_next_step(nine_pct_free):
    """A WARN with no actionable hint is just noise at 3am."""
    # Arrange
    out, _ = nine_pct_free
    # Act
    hinted = "sudo du -x -h -d1" in out
    # Assert
    assert hinted, out


# ── Case 3: 1% free bytes -> CRITICAL, non-zero exit ───────


def test_one_percent_free_exits_one(one_pct_free):
    """Critical must GATE, not merely print: the exit code has to be non-zero."""
    # Arrange
    out, rc = one_pct_free
    # Act
    observed = rc
    # Assert
    assert observed == 1, out


def test_one_percent_free_fails_on_bytes(one_pct_free):
    # Arrange
    out, _ = one_pct_free
    # Act
    byte_lines = _metric_lines(out, "bytes")
    # Assert
    assert all("[FAIL]" in ln for ln in byte_lines) and byte_lines, out


def test_critical_banner_cites_the_incident(one_pct_free):
    """The operator reading this at 3am should not have to reconstruct why."""
    # Arrange
    out, _ = one_pct_free
    # Act
    cited = "2026-08-09" in out
    # Assert
    assert cited, out


# ── Case 4: 92% inodes with bytes to spare -> WARN on inodes ──


def test_inode_exhaustion_exits_two(inodes_92_pct_used):
    # Arrange
    out, rc = inodes_92_pct_used
    # Act
    observed = rc
    # Assert
    assert observed == 2, out


def test_inode_exhaustion_warns_on_inodes(inodes_92_pct_used):
    """The exact metric that was at 92% during the incident, and never alarmed."""
    # Arrange
    out, _ = inodes_92_pct_used
    # Act
    inode_lines = _metric_lines(out, "inodes")
    # Assert
    assert all("[WARN]" in ln for ln in inode_lines) and inode_lines, out


def test_inode_exhaustion_leaves_the_bytes_line_ok(inodes_92_pct_used):
    """Independence: 66% of bytes are still free, so bytes must stay green.

    This is what a bytes-only check would have shown — and why it would have
    missed the incident entirely.
    """
    # Arrange
    out, _ = inodes_92_pct_used
    # Act
    byte_lines = _metric_lines(out, "bytes")
    # Assert
    assert all("[OK]" in ln for ln in byte_lines) and byte_lines, out


def test_inode_warning_names_the_inode_specific_fix(inodes_92_pct_used):
    """`du -h` finds bytes, not inodes. The hint must say `du --inodes`."""
    # Arrange
    out, _ = inodes_92_pct_used
    # Act
    hinted = "--inodes" in out
    # Assert
    assert hinted, out


# ── Case 5: df errors while measuring -> UNKNOWN, never OK ──


def test_unmeasurable_volume_exits_two(df_errors_while_measuring):
    # Arrange
    out, rc = df_errors_while_measuring
    # Act
    observed = rc
    # Assert
    assert observed == 2, out


def test_unmeasurable_volume_is_reported_unknown(df_errors_while_measuring):
    # Arrange
    out, _ = df_errors_while_measuring
    # Act
    reported = "[UNKNOWN]" in out
    # Assert
    assert reported, out


def test_unmeasurable_volume_never_reads_as_healthy(df_errors_while_measuring):
    """No silent fallback: a volume df could not measure is not a green volume."""
    # Arrange
    out, _ = df_errors_while_measuring
    # Act
    ok_lines = [ln for ln in out.splitlines() if "[OK]" in ln]
    # Assert
    assert ok_lines == [], out


def test_unmeasurable_volume_surfaces_the_real_df_error(df_errors_while_measuring):
    """Errors carry the offending value, not a generic 'could not check'."""
    # Arrange
    out, _ = df_errors_while_measuring
    # Act
    surfaced = "Input/output error" in out
    # Assert
    assert surfaced, out


# ── Structural guards ──────────────────────────────────────


def test_one_filesystem_yields_one_bytes_row(healthy):
    """Repo and home on one pool must alarm once, not twice."""
    # Arrange
    out, _ = healthy
    # Act
    byte_lines = _metric_lines(out, "bytes")
    # Assert
    assert len(byte_lines) == 1, out


def test_one_filesystem_yields_one_inode_row(healthy):
    # Arrange
    out, _ = healthy
    # Act
    inode_lines = _metric_lines(out, "inodes")
    # Assert
    assert len(inode_lines) == 1, out


def test_merged_row_names_both_roles(healthy):
    """Deduping must not hide which paths the single row accounts for."""
    # Arrange
    out, _ = healthy
    # Act
    labelled = "[repo+home]" in out
    # Assert
    assert labelled, out


@pytest.fixture(scope="module")
def separate_filesystem():
    """A path on a different filesystem from the repo, or skip."""
    other = "/dev/shm"
    if not os.path.isdir(other) or os.stat(other).st_dev == os.stat(REPO_ROOT).st_dev:
        pytest.skip(f"{other} is not a separate filesystem on this host")
    return other


def test_distinct_filesystems_yield_two_bytes_rows(fake_df_dir, separate_filesystem):
    """The dedupe must GROUP, not collapse: two pools still get two rows."""
    # Arrange
    home = separate_filesystem
    # Act
    out, _ = _run_check(fake_df_dir, "healthy", home=home)
    # Assert
    assert len(_metric_lines(out, "bytes")) == 2, out


def test_check_is_wired_into_make_status():
    """An alarm nobody runs is not an alarm."""
    # Arrange
    status = STATUS_SH.read_text(encoding="utf-8")
    # Act
    wired = [
        ln
        for ln in status.splitlines()
        if "check_disk_space.sh" in ln and not ln.lstrip().startswith("#")
    ]
    # Assert
    assert len(wired) == 1 and wired[0].rstrip().endswith("&"), wired


def test_check_is_executable():
    """check-status.sh invokes the path directly, so the mode bit is load-bearing."""
    # Arrange
    path = CHECK_SH
    # Act
    executable = path.is_file() and os.access(path, os.X_OK)
    # Assert
    assert executable, f"chmod +x {path}"


def test_warn_threshold_is_ten_percent():
    """If this is renamed or retuned, the mutation cases above must be revisited."""
    # Arrange
    script = CHECK_SH.read_text(encoding="utf-8")
    # Act
    declared = "WARN_FREE_PCT=10" in script
    # Assert
    assert declared


def test_critical_threshold_is_two_percent():
    # Arrange
    script = CHECK_SH.read_text(encoding="utf-8")
    # Act
    declared = "CRIT_FREE_PCT=2" in script
    # Assert
    assert declared
