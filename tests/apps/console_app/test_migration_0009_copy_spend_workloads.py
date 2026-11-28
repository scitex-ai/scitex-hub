"""console_app 0009 folds spend_app.WorkloadSession rows into the console table.

Runs the real migrations on the test database: rewind to the state before the
fold, write rows the way both writers used to, migrate forward (and back).
"""

from __future__ import annotations

from datetime import timedelta

import pytest
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.utils import timezone

BEFORE = [
    ("console_app", "0008_workloadsession_spend_fields"),
    ("spend_app", "0001_initial"),
]
AFTER = [
    ("console_app", "0009_copy_spend_workloads"),
    ("spend_app", "0002_delete_workloadsession"),
]


def _migrate(targets):
    executor = MigrationExecutor(connection)
    executor.migrate(targets)
    return MigrationExecutor(connection).loader.project_state(targets).apps


@pytest.fixture
def before_fold(transactional_db):
    """Rows as the double write left them, in the pre-fold schema."""
    old = _migrate(BEFORE)
    User = old.get_model("auth", "User")
    Spend = old.get_model("spend_app", "WorkloadSession")
    Console = old.get_model("console_app", "WorkloadSession")
    user = User.objects.create(username="migrated-spender", password="unused")
    now = timezone.now()
    hour_ago = now - timedelta(hours=1)
    # A job written by BOTH writers: one launch, two rows.
    Console.objects.create(
        user_id=user.pk,
        workload="job",
        scheduler="slurm",
        scheduler_job_id="9001",
        host="hub",
        started_at=hour_ago,
    )
    Spend.objects.create(
        user_id=user.pk,
        kind="job",
        cpus=4,
        memory_gb=16,
        max_seconds=7200,
        scheduler_id="9001",
        label="scitex_u_run",
        started_at=hour_ago,
    )
    # A service only spend_app recorded.
    Spend.objects.create(
        user_id=user.pk,
        kind="service",
        scheduler_id="svc-uuid",
        label="tensorboard",
        started_at=hour_ago,
        stopped_at=now,
        stop_reason="user",
    )
    yield {"user_id": user.pk}
    _migrate(MigrationExecutor(connection).loader.graph.leaf_nodes())


def _console(apps, user_id):
    return apps.get_model("console_app", "WorkloadSession").objects.filter(
        user_id=user_id
    )


def test_the_fold_leaves_one_row_per_launch(before_fold):
    # Arrange
    user_id = before_fold["user_id"]
    # Act
    new = _migrate(AFTER)
    # Assert
    assert _console(new, user_id).count() == 2


def test_a_job_row_takes_the_spend_rows_allocation(before_fold):
    # Arrange
    user_id = before_fold["user_id"]
    # Act
    new = _migrate(AFTER)
    # Assert
    row = _console(new, user_id).get(workload="job")
    assert (row.cpus, row.memory_gb, row.max_seconds, row.label) == (
        4,
        16,
        7200,
        "scitex_u_run",
    )


def test_a_service_only_spend_recorded_is_copied(before_fold):
    # Arrange
    user_id = before_fold["user_id"]
    # Act
    new = _migrate(AFTER)
    # Assert
    row = _console(new, user_id).get(workload="service")
    assert (row.scheduler, row.scheduler_job_id, row.stop_reason) == (
        "local",
        "svc-uuid",
        "user",
    )


def test_migrating_back_restores_the_spend_rows(before_fold):
    # Arrange
    user_id = before_fold["user_id"]
    _migrate(AFTER)
    # Act
    old = _migrate(BEFORE)
    # Assert
    spend = old.get_model("spend_app", "WorkloadSession").objects.filter(
        user_id=user_id
    )
    assert sorted(spend.values_list("kind", "scheduler_id")) == [
        ("job", "9001"),
        ("service", "svc-uuid"),
    ]


def test_migrating_back_drops_only_the_rows_the_fold_created(before_fold):
    # Arrange
    user_id = before_fold["user_id"]
    _migrate(AFTER)
    # Act
    old = _migrate(BEFORE)
    # Assert
    assert list(_console(old, user_id).values_list("workload", flat=True)) == ["job"]
