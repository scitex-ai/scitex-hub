"""provision_compute_user prints the node commands; it never runs them unasked."""

from io import StringIO

import pytest
from django.contrib.auth.models import User
from django.core.management import call_command

from apps.workspace.console_app.models import ComputeIdentity


def _run(username):
    out = StringIO()
    call_command("provision_compute_user", username, "--nodes=node-a", stdout=out)
    return out.getvalue()


@pytest.mark.django_db
def test_prints_useradd_with_the_allocated_uid():
    # Arrange
    User.objects.create_user(username="alice")
    # Act
    output = _run("alice")
    # Assert
    uid = ComputeIdentity.objects.get(username="alice").uid
    assert f"useradd -u {uid} -g {uid}" in output


@pytest.mark.django_db
def test_dry_run_targets_the_named_node():
    # Arrange
    User.objects.create_user(username="alice")
    # Act
    output = _run("alice")
    # Assert
    assert output.splitlines()[1].startswith("ssh node-a ")
