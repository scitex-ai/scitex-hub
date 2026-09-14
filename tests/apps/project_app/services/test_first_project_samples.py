#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""A new "SciTeX Minimal" project carries sample data, a figure recipe and references."""

import pytest

from apps.infra.project_app.services.first_project_samples import (
    SAMPLE_RELPATHS,
    seed_first_project_samples,
)
from apps.infra.project_app.services.writer_workspace_layout import (
    WRITER_WORKSPACE_RELPATH,
)


@pytest.fixture(name="minimal_project")
def _minimal_project(tmp_path):
    from scitex.template import clone_template

    project_path = tmp_path / "first-project"
    clone_template(template_id="minimal", project_dir=str(project_path), git_strategy=None)
    seed_first_project_samples(project_path)
    return project_path


def test_sample_files_exist_in_a_new_minimal_project(minimal_project):
    # Arrange
    expected = list(SAMPLE_RELPATHS)
    # Act
    missing = [relpath for relpath in expected if not (minimal_project / relpath).is_file()]
    # Assert
    assert missing == []


def test_minimal_project_abstract_is_no_longer_the_placeholder(minimal_project):
    # Arrange
    abstract = minimal_project / WRITER_WORKSPACE_RELPATH / "01_manuscript/contents/abstract.tex"
    # Act
    text = abstract.read_text(encoding="utf-8")
    # Assert
    assert "data/sample.csv" in text


# EOF
