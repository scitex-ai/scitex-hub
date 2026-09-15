"""X2PDF jobs: a directory per conversion under the user's hidden cache.

The job directory lives under the user's data root, which both the web and the
Celery worker containers mount, so either side can run the conversion. A
``claim`` file created with O_EXCL makes sure only one of them does.
"""

from __future__ import annotations

import json
import logging
import os
import re
import shutil
import tempfile
import time
import uuid
from pathlib import Path, PurePosixPath

from apps.infra.platform_app.services.paths import resolve_within
from apps.infra.project_app.services.filesystem.permissions import get_user_data_root
from apps.security import safe_log_field

from .convert import ConversionError, convert_file, convert_url
from .naming import derive_pdf_filename

logger = logging.getLogger(__name__)

_JOB_ID = re.compile(r"^[0-9a-f]{32}$")
JOB_TTL_S = 24 * 3600
# If no worker has picked a job up by then, the web process runs it itself.
QUEUE_GRACE_S = 12


def jobs_root(user) -> Path:
    user_data_root = get_user_data_root(user)
    root = resolve_within(user_data_root, ".cache/x2pdf")
    if root is None:  # Defensive: the static fragment must always be contained.
        raise RuntimeError("Invalid X2PDF jobs root")
    root.mkdir(parents=True, exist_ok=True)
    return root


def job_dir(user, job_id: str) -> Path | None:
    if not isinstance(job_id, str) or not _JOB_ID.match(job_id):
        return None
    path = resolve_within(jobs_root(user), job_id)
    return path if path is not None and path.is_dir() else None


def read_meta(path: Path) -> dict:
    target = resolve_within(path, "meta.json")
    if target is None:
        return {"status": "error", "error": "Job metadata is missing."}
    try:
        return json.loads(target.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"status": "error", "error": "Job metadata is missing."}


def write_meta(path: Path, meta: dict) -> None:
    job_root = resolve_within(path, "")
    target = resolve_within(path, "meta.json")
    if job_root is None or target is None:
        raise ValueError("Invalid job path")
    fd, tmp = tempfile.mkstemp(dir=job_root, prefix=".meta")
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        json.dump(meta, fh, ensure_ascii=False)
    os.replace(tmp, target)


def _sweep(root: Path) -> None:
    cutoff = time.time() - JOB_TTL_S
    for child in root.iterdir():
        try:
            safe_child = resolve_within(root, child.name)
            if (
                safe_child is not None
                and safe_child.is_dir()
                and safe_child.stat().st_mtime < cutoff
            ):
                shutil.rmtree(safe_child, ignore_errors=True)
        except OSError:
            continue


def create_job(user, *, upload=None, url: str | None = None) -> str:
    root = jobs_root(user)
    _sweep(root)
    job_id = uuid.uuid4().hex
    path = resolve_within(root, job_id)
    if path is None:
        raise RuntimeError("Invalid X2PDF job id")
    path.mkdir()
    meta = {"status": "queued", "created": time.time()}
    if upload is not None:
        name = (
            PurePosixPath((upload.name or "file").replace("\\", "/")).name[:200]
            or "file"
        )
        suffix = re.sub(r"[^a-z0-9.]", "", PurePosixPath(name.lower()).suffix)[:12]
        stored = f"input{suffix}"
        target = resolve_within(path, stored)
        if target is None:
            raise RuntimeError("Invalid X2PDF upload path")
        with open(target, "wb") as fh:
            for chunk in upload.chunks():
                fh.write(chunk)
        meta.update(source="file", original_name=name, stored=stored)
    else:
        meta.update(source="url", url=url)
    write_meta(path, meta)
    return job_id


def claim(path: Path) -> bool:
    target = resolve_within(path, "claim")
    if target is None:
        return False
    try:
        os.close(os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600))
        return True
    except FileExistsError:
        return False


def run_job(path: Path) -> dict:
    """Convert once; a second caller finds the claim taken and returns the meta."""
    if not claim(path):
        return read_meta(path)
    meta = read_meta(path)
    meta.update(status="running", started=time.time())
    write_meta(path, meta)
    work = resolve_within(path, "work")
    output = resolve_within(path, "output.pdf")
    if work is None or output is None:
        meta.update(status="error", error="Invalid conversion job path.")
        return meta
    work.mkdir(exist_ok=True)
    try:
        if meta.get("source") == "url":
            result = convert_url(meta["url"], work, job_root=path)
        else:
            source = resolve_within(path, meta.get("stored"))
            if source is None:
                raise ConversionError("Conversion path leaves the job directory.")
            result = convert_file(source, work, meta["original_name"], job_root=path)
        os.replace(result.pdf_path, output)
        meta.update(
            status="done",
            kind=result.kind,
            title=result.title,
            pages=result.pages,
            notes=result.notes,
            size=output.stat().st_size,
            filename=derive_pdf_filename(
                title=result.title,
                original_name=meta.get("original_name"),
                url=meta.get("url"),
            ),
        )
    except ConversionError as exc:
        meta.update(status="error", error=str(exc))
    except Exception:
        logger.exception("x2pdf conversion crashed (%s)", safe_log_field(path.name))
        meta.update(status="error", error="Conversion failed unexpectedly.")
    finally:
        shutil.rmtree(work, ignore_errors=True)
    meta["finished"] = time.time()
    write_meta(path, meta)
    return meta


def is_stale_queued(meta: dict) -> bool:
    return (
        meta.get("status") == "queued"
        and time.time() - meta.get("created", 0) > QUEUE_GRACE_S
    )
