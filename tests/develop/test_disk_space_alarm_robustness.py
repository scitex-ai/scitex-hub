"""Disk & inode alarm: prove it survives the conditions it exists to report.

``test_disk_space_alarm.py`` next door proves the alarm fires on a full disk.
This file proves it still fires when the *environment* is degraded — which is
not a hypothetical, because every degradation below was measured against the
first revision of the shipped script and every one of them defeated it:

    a full disk breaks mktemp   -> severity INVERTED: 100% full reported a
                                   yellow warning, printed no numbers at all,
                                   gave an EMPTY reason string, and leaked raw
                                   bash errors into `make status`
    fs with no inode table      -> permanent [UNKNOWN] + permanent exit 2 on
                                   any host whose df reports inode total 0
                                   (btrfs; 14 such mounts on the dev host,
                                   and zero mounts reporting the "-" the code
                                   was actually written for)
    bytes probe fails alone     -> the inode probe was skipped entirely, so a
                                   reader saw one [UNKNOWN] for bytes and
                                   concluded inodes were fine
    source name with a space    -> a CIFS share at 100% full parsed as
                                   non-numeric and reported [UNKNOWN] + exit 2
                                   instead of [FAIL] + exit 1
    only repo+home watched      -> `/` and Docker's data root, where this
                                   Docker-only project's volumes actually
                                   live, were never measured at all

The first is the headline. /tmp is the SAME filesystem this check watches on
every host we run on, so at zero bytes free the script's own scratch file got
ENOSPC — the check broke exactly when its subject broke, which is worse than
having no check. Each case below re-injects the degradation end-to-end through
the shipped script.

No Docker and no secrets required, so this runs in the headless pytest matrix.
"""

import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
CHECK_SH = REPO_ROOT / "scripts" / "maintenance" / "check_disk_space.sh"

# Resolved once, from the AMBIENT PATH, and invoked by absolute path. Cases
# below hand `_run` a narrowed PATH to hide a tool from the script; resolving
# the interpreter through that same narrowed PATH would let a case delete the
# thing meant to run the script under test.
BASH = shutil.which("bash") or "/bin/bash"

# Synthetic df covering the degraded shapes. FAKE_DF_MODE picks one.
FAKE_DF = r"""#!/bin/bash
mode="${FAKE_DF_MODE:?FAKE_DF_MODE must be set}"

want_inodes=0
for arg in "$@"; do
    [ "$arg" = "-i" ] && want_inodes=1
done

BYTES_HEALTHY="/dev/fake 412316860 138804396 273512464  34% /fake"
INODES_HEALTHY="/dev/fake 26214400  1981572 24232828   8% /fake"

case "$mode" in
    healthy)
        bytes="$BYTES_HEALTHY"; inodes="$INODES_HEALTHY"
        ;;
    # Zero bytes free: the 2026-08-09 state, and the state in which the
    # script's own mktemp used to fail.
    full)
        bytes="/dev/fake 412316860 412316860         0 100% /fake"
        inodes="$INODES_HEALTHY"
        ;;
    # A filesystem with no fixed inode table. This line is copied VERBATIM
    # from the dev host's `df -P -i -a`: total is a plain 0, and the capacity
    # column is "-". 14 mounts there print this shape; none print the
    # "-"-total shape the original SKIP branch tested for.
    inode_zero)
        bytes="$BYTES_HEALTHY"
        inodes="mqueue                                   0       0        0     - /dev/mqueue"
        ;;
    # `df -P -k` and `df -P -i` are separate calls that fail independently.
    bytes_error)
        if [ "$want_inodes" -eq 1 ]; then
            inodes="$INODES_HEALTHY"
        else
            echo "df: cannot read table of mounted file systems: Input/output error" >&2
            exit 1
        fi
        ;;
    # A CIFS share whose SOURCE contains a space, at 100% full. df -P quotes
    # nothing, so counting columns from the left mis-parses this row.
    space_src)
        bytes="//nas/Home Videos 412316860 412316860         0 100% /mnt/media"
        inodes="//nas/Home Videos 26214400  1981572 24232828   8% /mnt/media"
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

# What mktemp really does once the watched filesystem has no bytes left.
FAILING_MKTEMP = r"""#!/bin/bash
echo "mktemp: failed to create file via template '/tmp/tmp.XXXXXXXXXX': No space left on device" >&2
exit 1
"""

# Stands in for a Docker install; answers `docker info --format ...`.
FAKE_DOCKER = r"""#!/bin/bash
echo "${FAKE_DOCKER_ROOT:?FAKE_DOCKER_ROOT must be set}"
"""

ANSI = re.compile(r"\x1b\[[0-9;]*m")
# emit_metric prints "<source> [<labels>] at <mount>"; labels join with "+".
LABEL_GROUP = re.compile(r"\[([a-z+]+)\] at ")
ALARM_TOKENS = ("[WARN]", "[FAIL]", "[UNKNOWN]")


def _write_bin(directory, name, body):
    path = Path(directory) / name
    path.write_text(body, encoding="utf-8")
    path.chmod(0o755)
    return path


def _run(path_dirs, mode, targets=None, extra_env=None):
    """Run the shipped check. Returns (stdout, stderr, exit code).

    ``targets`` pins SCITEX_DISK_TARGETS; pass ``None`` to exercise the
    script's own default target list.
    """
    env = dict(os.environ)
    prefix = os.pathsep.join(str(d) for d in path_dirs)
    env["PATH"] = f"{prefix}{os.pathsep}{env['PATH']}"
    env["FAKE_DF_MODE"] = mode
    env["HOME"] = str(REPO_ROOT)
    env.pop("SCITEX_DISK_TARGETS", None)
    if targets is not None:
        env["SCITEX_DISK_TARGETS"] = targets
    if extra_env:
        env.update(extra_env)
    proc = subprocess.run(
        [BASH, str(CHECK_SH)],
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )
    return ANSI.sub("", proc.stdout), ANSI.sub("", proc.stderr), proc.returncode


def _metric_lines(out, metric):
    return [ln for ln in out.splitlines() if f" {metric} " in ln and "[" in ln]


def _label_components(out):
    """Every role name the report accounts for, e.g. {"repo", "home", "root"}."""
    found = set()
    for group in LABEL_GROUP.findall(out):
        found.update(group.split("+"))
    return found


PINNED = f"repo={REPO_ROOT} home={REPO_ROOT}"


@pytest.fixture(scope="module")
def fake_bin(tmp_path_factory):
    """A PATH entry holding the synthetic df."""
    d = tmp_path_factory.mktemp("fake-bin")
    _write_bin(d, "df", FAKE_DF)
    return d


@pytest.fixture(scope="module")
def nospace_bin(tmp_path_factory):
    """A PATH entry holding ONLY a failing mktemp, injected on top of fake_bin."""
    d = tmp_path_factory.mktemp("nospace-bin")
    _write_bin(d, "mktemp", FAILING_MKTEMP)
    return d


@pytest.fixture(scope="module")
def full_disk_without_mktemp(fake_bin, nospace_bin):
    """100% full AND mktemp refusing to work — the two happen together."""
    return _run([nospace_bin, fake_bin], "full", targets=PINNED)


# ── The alarm must survive a disk with no room for a temp file ──


def test_full_disk_reports_critical_even_when_mktemp_fails(full_disk_without_mktemp):
    """The defect this file exists for: severity used to INVERT to a warning."""
    # Arrange
    out, _, _ = full_disk_without_mktemp
    # Act
    byte_lines = _metric_lines(out, "bytes")
    # Assert
    assert byte_lines and all("[FAIL]" in ln for ln in byte_lines), out


def test_full_disk_still_gates_when_mktemp_fails(full_disk_without_mktemp):
    """Exit 1 is what a cron job or deploy gate reads. It used to be exit 2."""
    # Arrange
    _, _, rc = full_disk_without_mktemp
    # Act
    observed = rc
    # Assert
    assert observed == 1, full_disk_without_mktemp[0]


def test_full_disk_still_prints_the_measurement_when_mktemp_fails(
    full_disk_without_mktemp,
):
    """df could answer the whole time; the broken scratch file hid the numbers."""
    # Arrange
    out, _, _ = full_disk_without_mktemp
    # Act
    measured = "0.0% free" in out and "393G" in out
    # Assert
    assert measured, out


def test_failing_mktemp_produces_no_unknown_rows(full_disk_without_mktemp):
    """An unmeasurable volume is a real signal — it must not be manufactured."""
    # Arrange
    out, _, _ = full_disk_without_mktemp
    # Act
    unknown = [ln for ln in out.splitlines() if "[UNKNOWN]" in ln]
    # Assert
    assert unknown == [], out


def test_failing_mktemp_leaks_no_bash_noise_into_make_status(
    full_disk_without_mktemp,
):
    """`make status` used to collect four raw 'No such file or directory' lines."""
    # Arrange
    _, err, _ = full_disk_without_mktemp
    # Act
    noise = err.strip()
    # Assert
    assert noise == "", err


# ── A filesystem with no inode table is not an unmeasurable one ──


@pytest.fixture(scope="module")
def no_inode_table(fake_bin):
    return _run([fake_bin], "inode_zero", targets=PINNED)


def test_zero_inode_total_is_skipped_not_unknown(no_inode_table):
    """btrfs and friends report total 0. There is no inode budget to run out of."""
    # Arrange
    out, _, _ = no_inode_table
    # Act
    inode_lines = _metric_lines(out, "inodes")
    # Assert
    assert inode_lines and all("[SKIP]" in ln for ln in inode_lines), out


def test_zero_inode_total_raises_no_alarm(no_inode_table):
    """This shape used to pin such a host to a yellow line and exit 2 forever."""
    # Arrange
    out, _, _ = no_inode_table
    # Act
    fired = [token for token in ALARM_TOKENS if token in out]
    # Assert
    assert fired == [], out


def test_zero_inode_total_exits_zero(no_inode_table):
    # Arrange
    out, _, rc = no_inode_table
    # Act
    observed = rc
    # Assert
    assert observed == 0, out


def test_zero_inode_total_leaves_the_bytes_line_measured(no_inode_table):
    """Skipping inodes must not cost the bytes reading on the same volume."""
    # Arrange
    out, _, _ = no_inode_table
    # Act
    byte_lines = _metric_lines(out, "bytes")
    # Assert
    assert byte_lines and all("[OK]" in ln for ln in byte_lines), out


# ── One failing metric must not silence the other ──


@pytest.fixture(scope="module")
def bytes_probe_fails(fake_bin):
    return _run([fake_bin], "bytes_error", targets=PINNED)


def test_failed_bytes_probe_still_reports_bytes_unknown(bytes_probe_fails):
    # Arrange
    out, _, _ = bytes_probe_fails
    # Act
    byte_lines = _metric_lines(out, "bytes")
    # Assert
    assert byte_lines and all("[UNKNOWN]" in ln for ln in byte_lines), out


def test_failed_bytes_probe_still_reports_the_inode_line(bytes_probe_fails):
    """The header promises one line per metric. A missing line reads as 'fine'."""
    # Arrange
    out, _, _ = bytes_probe_fails
    # Act
    inode_lines = _metric_lines(out, "inodes")
    # Assert
    assert len(inode_lines) == 1, out


def test_failed_bytes_probe_measures_inodes_normally(bytes_probe_fails):
    """Inodes are healthy here, and must be *reported* healthy, not inherited."""
    # Arrange
    out, _, _ = bytes_probe_fails
    # Act
    inode_lines = _metric_lines(out, "inodes")
    # Assert
    assert all("[OK]" in ln for ln in inode_lines), out


# ── A source name containing a space must still parse ──


@pytest.fixture(scope="module")
def cifs_source_with_space(fake_bin):
    return _run([fake_bin], "space_src", targets=PINNED)


def test_source_with_a_space_at_100_percent_reports_critical(cifs_source_with_space):
    """Mis-parsing errs toward UNDER-alarming, on a project that ships to a NAS."""
    # Arrange
    out, _, _ = cifs_source_with_space
    # Act
    byte_lines = _metric_lines(out, "bytes")
    # Assert
    assert byte_lines and all("[FAIL]" in ln for ln in byte_lines), out


def test_source_with_a_space_gates(cifs_source_with_space):
    # Arrange
    out, _, rc = cifs_source_with_space
    # Act
    observed = rc
    # Assert
    assert observed == 1, out


def test_source_with_a_space_is_reported_whole(cifs_source_with_space):
    """The operator has to recognise the share, so print its real name."""
    # Arrange
    out, _, _ = cifs_source_with_space
    # Act
    named = "//nas/Home Videos" in out
    # Assert
    assert named, out


def test_source_with_a_space_keeps_the_mount_point_intact(cifs_source_with_space):
    """The hint pastes this mount into a du command; a truncated one is useless."""
    # Arrange
    out, _, _ = cifs_source_with_space
    # Act
    hinted = "sudo du -x -h -d1 /mnt/media" in out
    # Assert
    assert hinted, out


# ── Which volumes get watched ──


@pytest.fixture(scope="module")
def default_targets_with_docker(fake_bin, tmp_path_factory):
    """The script's own target list, on a host where Docker answers."""
    docker_bin = tmp_path_factory.mktemp("docker-bin")
    _write_bin(docker_bin, "docker", FAKE_DOCKER)
    root = tmp_path_factory.mktemp("docker-root")
    return _run(
        [docker_bin, fake_bin],
        "healthy",
        targets=None,
        extra_env={"FAKE_DOCKER_ROOT": str(root)},
    )


def test_default_targets_include_the_root_filesystem(default_targets_with_docker):
    """`/` is a different filesystem from the repo on the dev host, and was blind."""
    # Arrange
    out, _, _ = default_targets_with_docker
    # Act
    components = _label_components(out)
    # Assert
    assert "root" in components, out


def test_default_targets_include_the_docker_data_root(default_targets_with_docker):
    """This is a Docker-only project: its volumes are what actually fill up."""
    # Arrange
    out, _, _ = default_targets_with_docker
    # Act
    components = _label_components(out)
    # Assert
    assert "docker" in components, out


def _path_hiding_docker(head, shadow, source_path=None):
    """A PATH identical to ``source_path`` except that ``docker`` is absent.

    ``source_path`` defaults to the ambient ``PATH``; callers pass one
    explicitly so the behaviour can be exercised against a directory shaped
    like the host that broke, on a host that is not shaped that way.

    Hiding Docker is a per-BINARY intent, and it must not be expressed by
    dropping whole PATH directories. On Ubuntu ``docker`` and ``bash`` share
    ``/usr/bin``, so dropping the directory that holds Docker also deletes the
    interpreter -- which is exactly what happened: every case using this PATH
    errored at setup with ``FileNotFoundError: 'bash'`` on all three matrix
    legs, while passing locally where Docker lives elsewhere.

    So each directory holding a ``docker`` is replaced by ``shadow``: symlinks
    to everything in it except ``docker``. Nothing else the script needs -- df,
    awk, sed, mktemp, bash -- disappears with it.
    """
    if source_path is None:
        source_path = os.environ.get("PATH", "")
    entries = [str(head), str(shadow)]
    for entry in source_path.split(os.pathsep):
        if not entry:
            continue
        if not os.path.exists(os.path.join(entry, "docker")):
            entries.append(entry)
            continue
        try:
            names = os.listdir(entry)
        except OSError:
            continue
        for name in names:
            if name == "docker":
                continue
            link = Path(shadow) / name
            if link.exists() or link.is_symlink():
                continue
            try:
                link.symlink_to(os.path.join(entry, name))
            except OSError:
                pass
    return os.pathsep.join(entries)


@pytest.fixture(scope="module")
def path_without_docker(fake_bin, tmp_path_factory):
    """PATH for a host with no Docker, with every other tool still present."""
    return _path_hiding_docker(fake_bin, tmp_path_factory.mktemp("no-docker-bin"))


@pytest.fixture(scope="module")
def default_targets_without_docker(fake_bin, path_without_docker):
    """The default target list on a host with no Docker at all."""
    return _run(
        [fake_bin],
        "healthy",
        targets=None,
        extra_env={"PATH": path_without_docker},
    )


@pytest.fixture
def path_from_shared_bin(tmp_path):
    """``_path_hiding_docker`` applied to one dir holding docker AND bash.

    Real files in ``tmp_path``, passed in explicitly -- nothing is patched.
    Built synthetically rather than read from the host because this container
    has no ``docker`` on PATH at all, so an ambient-PATH check would drop
    nothing, assert nothing, and pass on a machine that cannot reproduce the
    bug. The directory below is the Ubuntu runner's ``/usr/bin`` shape -- the
    one that broke CI -- so these guards fail on the old implementation
    everywhere, not only where Docker happens to be installed.
    """
    shared = tmp_path / "usr-bin"
    shared.mkdir()
    for name in ("docker", "bash", "df"):
        binary = shared / name
        binary.write_text("#!/bin/sh\n")
        binary.chmod(0o755)
    head = tmp_path / "head"
    head.mkdir()
    shadow = tmp_path / "shadow"
    shadow.mkdir()
    return _path_hiding_docker(head, shadow, source_path=str(shared))


def test_hiding_docker_keeps_the_interpreter(path_from_shared_bin):
    """Removing Docker must not remove bash: they share /usr/bin on Ubuntu.

    Regression guard for the 2026-08-10 CI outage, where the no-Docker PATH
    dropped whole directories and took the interpreter with them.
    """
    # Arrange
    path = path_from_shared_bin
    # Act
    observed = shutil.which("bash", path=path)
    # Assert
    assert observed is not None, path


def test_hiding_docker_keeps_the_other_tools(path_from_shared_bin):
    """The script under test still needs df/awk/mktemp from that directory."""
    # Arrange
    path = path_from_shared_bin
    # Act
    observed = shutil.which("df", path=path)
    # Assert
    assert observed is not None, path


def test_hiding_docker_actually_hides_docker(path_from_shared_bin):
    """The two guards above must not be satisfied by keeping everything."""
    # Arrange
    path = path_from_shared_bin
    # Act
    observed = shutil.which("docker", path=path)
    # Assert
    assert observed is None, observed


def test_missing_docker_is_not_an_error(default_targets_without_docker):
    """Absent Docker means no Docker volume to watch — not a failure to report."""
    # Arrange
    out, _, rc = default_targets_without_docker
    # Act
    observed = rc
    # Assert
    assert observed == 0, out


def test_missing_docker_says_so_rather_than_staying_silent(
    default_targets_without_docker,
):
    """No silent fallback: an unwatched volume class must be stated, not implied."""
    # Arrange
    out, _, _ = default_targets_without_docker
    # Act
    stated = "docker is not installed" in out
    # Assert
    assert stated, out


def test_targets_env_var_replaces_the_default_list(fake_bin):
    """An operator must be able to point this at the volume that matters here."""
    # Arrange
    targets = f"cache=/dev/shm repo={REPO_ROOT}"
    # Act
    out, _, _ = _run([fake_bin], "healthy", targets=targets)
    # Assert
    assert _label_components(out) == {"cache", "repo"}, out


def test_targets_env_var_accepts_colon_separation(fake_bin):
    """Colon separation is the PATH convention, so accept it alongside spaces."""
    # Arrange
    targets = f"cache=/dev/shm:repo={REPO_ROOT}"
    # Act
    out, _, _ = _run([fake_bin], "healthy", targets=targets)
    # Assert
    assert _label_components(out) == {"cache", "repo"}, out


# ── Say which number this is ──


def test_bytes_line_labels_the_root_reserve(fake_bin):
    """df's Available excludes the root reserve while its size column does not.

    The percentage here is therefore smaller than df's own Capacity column
    implies. Errs safe, but two numbers that disagree and neither explains
    itself is a trap at 3am.
    """
    # Arrange
    out, _, _ = _run([fake_bin], "healthy", targets=PINNED)
    # Act
    byte_lines = _metric_lines(out, "bytes")
    # Assert
    assert byte_lines and all("available to non-root" in ln for ln in byte_lines), out
