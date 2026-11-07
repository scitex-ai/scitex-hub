"""Per-file atomic publication for the explicit demo coordinator, not Writer core."""

import os
import stat
import tempfile
from contextlib import contextmanager
from pathlib import Path

from ._mnist_facts import DemoSeedRefused, digest, jailed, read_member


def _identity(value):
    return (
        value.st_dev,
        value.st_ino,
        value.st_size,
        value.st_mode,
        value.st_mtime_ns,
        value.st_ctime_ns,
    )


def _ready_file(parent, data, mode):
    fd, name = tempfile.mkstemp(prefix=".mnist-section-", dir=parent)
    path = Path(name)
    try:
        with os.fdopen(fd, "wb") as stream:
            os.fchmod(stream.fileno(), mode)
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        return path
    except Exception:
        path.unlink(missing_ok=True)
        raise


@contextmanager
def stage_sections(root, rows, originals, rendered, path_for):
    """Run real Writer writes privately; preallocate new and rollback files.

    Each final replace is atomic. The complete batch is not a filesystem
    transaction; original backups remain the crash-recovery boundary.
    """
    from scitex_writer import Writer

    prepared = {}
    try:
        for row in rows:
            if row["action"] == "unchanged":
                continue
            target = jailed(root, path_for(row["section"]))
            observed = target.stat(follow_symlinks=False)
            if not stat.S_IMODE(observed.st_mode) & 0o222 or not os.access(
                target, os.W_OK
            ):
                raise DemoSeedRefused("Writer refused an explicitly read-only section")
            prepared[row["section"]] = {
                "identity": _identity(observed),
                "new": None,
                "old": None,
            }
        with tempfile.TemporaryDirectory(prefix="mnist-writer-candidate-") as directory:
            stage = Path(directory)
            for part in (
                "00_shared",
                "01_manuscript/contents",
                "02_supplementary",
                "03_revision",
            ):
                (stage / part).mkdir(parents=True, exist_ok=True)
            writer = Writer(stage, git_strategy=None)
            for name, item in prepared.items():
                if not writer.write_section(name, rendered[name]):
                    raise DemoSeedRefused("Writer refused the staged section write")
                data = read_member(stage, f"01_manuscript/contents/{name}.tex")
                if data != rendered[name].encode():
                    raise DemoSeedRefused(
                        "Staged Writer section differs from requested bytes"
                    )
                target = jailed(root, path_for(name))
                mode = stat.S_IMODE(item["identity"][3])
                item["new"] = _ready_file(target.parent, data, mode)
                item["old"] = _ready_file(target.parent, originals[name], mode)
            yield prepared
    finally:
        for item in prepared.values():
            for key in ("new", "old"):
                if item[key] is not None:
                    item[key].unlink(missing_ok=True)


def publish_section(root, relative, before_sha256, prepared):
    target = jailed(root, relative)
    if digest(read_member(root, relative)) != before_sha256:
        raise DemoSeedRefused("Section changed after plan admission")
    if _identity(target.stat(follow_symlinks=False)) != prepared["identity"]:
        raise DemoSeedRefused("Section identity changed before atomic publication")
    staged = prepared["new"].stat(follow_symlinks=False)
    os.replace(prepared["new"], target)
    published = target.stat(follow_symlinks=False)

    def stable(value):
        return (
            value.st_dev,
            value.st_ino,
            value.st_size,
            value.st_mode,
            value.st_mtime_ns,
        )

    if stable(staged) != stable(published):
        raise DemoSeedRefused("Published section was concurrently changed")
    prepared["published_identity"] = _identity(published)


def restore_section_if_ours(root, relative, after_sha256, prepared):
    """Never replace an edited/replaced/unreadable target during rollback."""
    try:
        target = jailed(root, relative)
        if digest(read_member(root, relative)) == after_sha256 and _identity(
            target.stat(follow_symlinks=False)
        ) == prepared.get("published_identity"):
            os.replace(prepared["old"], target)
    except (DemoSeedRefused, OSError):
        return
