"""Path and permission regressions for X2PDF job storage."""

import json
import os
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from apps.workspace.tools_app.x2pdf import convert, jobs


@pytest.fixture
def user():
    return SimpleNamespace(username="alice")


def test_job_dir_rejects_symlink_escape(tmp_path, user):
    root = tmp_path / "alice"
    outside = tmp_path / "outside"
    job_id = "a" * 32
    (root / ".cache" / "x2pdf").mkdir(parents=True)
    outside.mkdir()
    (root / ".cache" / "x2pdf" / job_id).symlink_to(outside, target_is_directory=True)
    with patch.object(jobs, "get_user_data_root", return_value=root):
        assert jobs.job_dir(user, job_id) is None


@pytest.mark.parametrize(
    "job_id", ["../" + "a" * 32, "/" + "a" * 32, "a" * 31, "a" * 32 + "/x"]
)
def test_job_dir_rejects_absolute_and_traversal_ids(tmp_path, user, job_id):
    root = tmp_path / "alice"
    (root / ".cache" / "x2pdf").mkdir(parents=True)
    with patch.object(jobs, "get_user_data_root", return_value=root):
        assert jobs.job_dir(user, job_id) is None


def test_claim_file_is_private(tmp_path):
    assert jobs.claim(tmp_path)
    assert (os.stat(tmp_path / "claim").st_mode & 0o777) == 0o600


def test_convert_file_rejects_source_outside_job_root(tmp_path):
    job = tmp_path / "job"
    work = job / "work"
    outside = tmp_path / "outside.txt"
    work.mkdir(parents=True)
    outside.write_text("secret")
    with pytest.raises(convert.ConversionError, match="job directory"):
        convert.convert_file(outside, work, "outside.txt", job_root=job)


def test_convert_file_rejects_symlink_source_escape(tmp_path):
    job = tmp_path / "job"
    work = job / "work"
    outside = tmp_path / "outside.txt"
    work.mkdir(parents=True)
    outside.write_text("secret")
    (job / "input.txt").symlink_to(outside)
    with pytest.raises(convert.ConversionError, match="job directory"):
        convert.convert_file(job / "input.txt", work, "input.txt", job_root=job)


def test_run_job_rejects_stored_path_traversal(tmp_path):
    job = tmp_path / "job"
    job.mkdir()
    outside = tmp_path / "secret.txt"
    outside.write_text("secret")
    (job / "meta.json").write_text(
        json.dumps(
            {"source": "file", "stored": "../secret.txt", "original_name": "x.txt"}
        )
    )
    result = jobs.run_job(job)
    assert result["status"] == "error"
    assert outside.read_text() == "secret"
