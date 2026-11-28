"""The batch-job API attributes a job only to a project the user can access."""

import pytest
from django.contrib.auth.models import User

from apps.infra.project_app.models import Project
from apps.workspace.console_app.job_api_views import resolve_job_project
from apps.workspace.console_app.services.slurm.tags import NO_PROJECT


@pytest.fixture
def alice(db):
    return User.objects.create_user(username="alice")


@pytest.fixture
def bobs_project(db):
    bob = User.objects.create_user(username="bob")
    return Project.objects.create(owner=bob, name="Bob", slug="bob-proj")


@pytest.mark.django_db
def test_omitted_project_means_no_project(alice):
    # Arrange
    body = {"script_path": "/workspace/run.py"}
    # Act
    project = resolve_job_project(alice, body)
    # Assert
    assert project is NO_PROJECT


@pytest.mark.django_db
def test_own_project_is_accepted(alice):
    # Arrange
    mine = Project.objects.create(owner=alice, name="Mine", slug="mine")
    # Act
    project = resolve_job_project(alice, {"project_id": mine.id})
    # Assert
    assert project == mine.id


@pytest.mark.django_db
def test_someone_elses_project_is_not_found(alice, bobs_project):
    # Arrange
    body = {"project_id": bobs_project.id}
    # Act
    # Assert
    with pytest.raises(LookupError):
        resolve_job_project(alice, body)


@pytest.mark.django_db
@pytest.mark.parametrize("raw", ["1", "1\n#SBATCH --uid=0", 0, -3, True, 1.5])
def test_non_integer_project_is_rejected(alice, raw):
    # Arrange
    body = {"project_id": raw}
    # Act
    # Assert
    with pytest.raises(ValueError):
        resolve_job_project(alice, body)
