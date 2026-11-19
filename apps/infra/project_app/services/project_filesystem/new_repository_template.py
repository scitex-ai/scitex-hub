"""Apply a scaffold to a new Gitea clone while retaining its Git identity."""

import shutil
import subprocess
import tempfile
from pathlib import Path


def populate_new_repository(project_path: Path, populate) -> bool:
    """Populate only an untouched auto-initialized repository.

    The caller must additionally identify this as the new-project request.
    Existing research contents are never an eligible destination. Stage the
    scaffold first so a failed fetch leaves the initial repository intact.
    """
    initial_files = {"README.md", "LICENSE", ".gitignore"}
    if not (project_path / ".git").is_dir():
        return False
    for entry in project_path.iterdir():
        if entry.name == ".git":
            continue
        if entry.name not in initial_files or entry.is_symlink() or not entry.is_file():
            return False
    status = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=project_path,
        capture_output=True,
        text=True,
        timeout=10,
    )
    if status.returncode or status.stdout.strip():
        return False

    with tempfile.TemporaryDirectory(
        prefix=".scitex-template-", dir=project_path.parent
    ) as staging:
        source = Path(staging) / project_path.name
        if not populate(source):
            return False
        shutil.copytree(
            source,
            project_path,
            dirs_exist_ok=True,
            symlinks=True,
            ignore=shutil.ignore_patterns(".git"),
        )
    return True
