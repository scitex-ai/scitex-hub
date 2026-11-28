#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Creating a project from /new/, end to end, for EVERY tab the page offers.

Nothing here is simulated: a real Gitea (scripts/testing/start_test_gitea.sh),
the real template packages (scitex-template, scitex-writer) and the real view.
The "Recommended" template failed for every new user for a week (hub#1273)
while unit tests of each piece stayed green, because no test ever created a
project the way a user does. These do.

Without a Gitea token the module skips — the main pytest job runs without a
Gitea server on purpose. The dedicated workflow
(project-create-every-template.yml) sets SCITEX_HUB_REQUIRE_LIVE_GITEA=1, which
turns that skip into a failure so the job cannot pass by not running.
"""

from __future__ import annotations

import os
import re
import subprocess
import uuid
from pathlib import Path

import pytest
from django.conf import settings
from django.contrib.auth.models import User

from apps.infra.project_app.models import Project
from apps.infra.project_app.views.projects.create_helpers import (
    LOCAL_CREATION_TABS,
)

pytestmark = [pytest.mark.django_db(transaction=True), pytest.mark.integration]

# What each offered tab must leave in the working tree, beyond the common
# checks (git repository, everything committed and pushed). One path per tab
# is enough to prove the tab's own scaffold landed, not just Gitea's README.
SCAFFOLD_MARKERS = {
    "minimal": ".scitex/writer/01_manuscript",
    "full": ".scitex/template/MANIFEST.yaml",
    "app": "pyproject.toml",
    "blank": "README.md",
}


def _live_gitea_or_skip():
    if getattr(settings, "GITEA_TOKEN", ""):
        return
    reason = (
        "no Gitea token (SCITEX_HUB_GITEA_TOKEN_DEV); start one with "
        "scripts/testing/start_test_gitea.sh"
    )
    if os.environ.get("SCITEX_HUB_REQUIRE_LIVE_GITEA") == "1":
        pytest.fail(reason)
    pytest.skip(reason)


@pytest.fixture
def new_user(client, settings, tmp_path):
    """A fresh, non-staff account signed in, with its own data root."""
    _live_gitea_or_skip()
    settings.BASE_DIR = tmp_path
    username = f"new{uuid.uuid4().hex[:10]}"
    user = User.objects.create_user(
        username, email=f"{username}@example.invalid", password="pw-1234567890"
    )
    client.force_login(user)
    yield user
    for project in Project.objects.filter(owner=user):
        project.delete()  # post_delete removes the Gitea repository


def _project_dir(user, slug) -> Path:
    return Path(settings.BASE_DIR) / "data" / "users" / user.username / "proj" / slug


def _git(root, *args) -> str:
    return subprocess.run(
        ["git", "-C", str(root), *args],
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    ).stdout.strip()


def _gitea_branch_sha(owner, repo, branch="main"):
    from apps.infra.gitea_app.api_client import GiteaClient

    data = (
        GiteaClient()._request("GET", f"/repos/{owner}/{repo}/branches/{branch}").json()
    )
    return data["commit"]["id"]


def _form_for(tab, name):
    init_type, template_type = LOCAL_CREATION_TABS[tab]
    return {
        "name": name,
        "description": f"Created from the {tab} tab",
        "init_type": init_type,
        "template_type": template_type,
        "project_type": "local",
        "visibility": "private",
    }


def test_every_offered_local_tab_is_covered(client, new_user):
    # Arrange
    offered = set(
        re.findall(r'data-tab="([a-z]+)"', client.get("/new/").content.decode())
    )

    # Act
    local_tabs = offered - {"import", "remote"}  # need an outside URL / host

    # Assert
    assert local_tabs == set(LOCAL_CREATION_TABS) == set(SCAFFOLD_MARKERS)


@pytest.mark.parametrize("tab", sorted(LOCAL_CREATION_TABS))
def test_creating_from_each_tab_opens_the_project(client, new_user, tab):
    # Arrange
    name = f"first-{tab}-project" + ("-app" if tab == "app" else "")

    # Act
    response = client.post("/new/", _form_for(tab, name))

    # Assert
    project = Project.objects.filter(owner=new_user, name=name).first()
    root = _project_dir(new_user, project.slug) if project else None
    assert (
        response.status_code,
        response.get("Location"),
        (root / SCAFFOLD_MARKERS[tab]).exists() if root else None,
        _git(root, "status", "--porcelain") if root else None,
        (
            _git(root, "rev-parse", "HEAD")
            == _gitea_branch_sha(new_user.username, project.slug)
        )
        if root
        else None,
        client.get(f"/{new_user.username}/{project.slug}/").status_code
        if project
        else None,
    ) == (
        302,
        f"/{new_user.username}/{project.slug if project else '?'}/",
        True,
        "",
        True,
        200,
    )


@pytest.mark.guards(
    defect="a failed creation deleted the row but left the folder and lost the form"
)
def test_failed_creation_leaves_nothing_and_keeps_the_form(client, new_user, settings):
    # Arrange: a Writer template branch that does not exist makes the real
    # template step fail after Gitea has created and cloned the repository.
    settings.SCITEX_WRITER_TEMPLATE_BRANCH = "no-such-branch-hub-1273"
    form = _form_for("minimal", "doomed-project")

    # Act
    response = client.post("/new/", form)

    # Assert
    html = response.content.decode()
    assert (
        response.status_code,
        Project.objects.filter(owner=new_user).count(),
        _project_dir(new_user, "doomed-project").exists(),
        'value="doomed-project"' in html,
        form["description"] in html,
        "Nothing was kept" in html,
    ) == (200, 0, False, True, True, True)


@pytest.mark.guards(
    defect="a leftover folder made the retry with the same name fail silently"
)
def test_leftover_folder_is_reported_and_reconciled(client, new_user):
    # Arrange: what an earlier failed attempt used to leave behind.
    leftover = _project_dir(new_user, "retry-project")
    leftover.mkdir(parents=True)
    _git(leftover, "init", "-q", "-b", "main")
    (leftover / "README.md").write_text("half-created\n")

    # Act
    check = client.get("/api/project/check-name/", {"name": "retry-project"}).json()
    response = client.post("/new/", _form_for("blank", "retry-project"))

    # Assert
    project = Project.objects.filter(owner=new_user, name="retry-project").first()
    quarantine = leftover.parent.parent / ".project-leftovers"
    assert (
        check["available"],
        check.get("leftover"),
        response.status_code,
        project is not None and project.slug,
        _git(leftover, "status", "--porcelain"),
        len(list(quarantine.glob("retry-project-*"))),
    ) == (True, True, 302, "retry-project", "", 1)
