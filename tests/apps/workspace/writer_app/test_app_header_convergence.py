#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Hub writer_app header converges onto the writer leaf shape (10-19 audit).

The leaf (scitex-writer's writer/_app_header.html) owns the header
contract: identity = leaf label + LEAF version, picker = the leaf picker
partial in the project-selector slot, actions empty. The hub fork must
render that shape, not its own (hardcoded title, no version, inline
relocation JS).
"""

from importlib import metadata as _metadata

from django.contrib.auth.models import User
from django.test import Client, TestCase

from apps.infra.project_app.models import Project
from apps.infra.project_app.services.project_filesystem import (
    get_project_filesystem_manager,
)
from tests.apps.workspace.writer_app._old_direct_gate import (
    writer_old_direct_urls,
)

PASSWORD = "TestPass123!"  # pragma: allowlist secret


class AppHeaderConvergenceTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = User.objects.create_user(
            username="header-owner", password=PASSWORD
        )
        cls.project = Project.objects.create(
            slug="header-study",
            owner=cls.owner,
            name="header-study",
            visibility="private",
        )
        get_project_filesystem_manager(cls.owner).create_project_directory(
            cls.project, use_template=False
        )

    def _page(self):
        client = Client()
        client.login(username="header-owner", password=PASSWORD)
        with writer_old_direct_urls():
            return client.get(
                f"/apps/writer/old-direct/?project={self.owner.username}/{self.project.slug}"
            )

    def test_header_mount_carries_leaf_title(self):
        html = self._page().content.decode()
        assert 'data-app-title="SciTeX Writer"' in html

    def test_header_mount_carries_leaf_version_not_hub_version(self):
        from django.conf import settings

        html = self._page().content.decode()
        leaf_version = _metadata.version("scitex-writer")
        assert f'data-app-version="{leaf_version}"' in html
        hub_version = getattr(settings, "SCITEX_HUB_VERSION", "")
        if hub_version and hub_version != leaf_version:
            assert f'data-app-version="{hub_version}"' not in html

    def test_picker_is_the_leaf_partial_placed_by_leaf_script(self):
        html = self._page().content.decode()
        assert "writer/css/project-picker.css" in html
        assert "writer/js/header-picker.js" in html

    def test_fork_leftovers_are_gone(self):
        html = self._page().content.decode()
        assert "writer-picker-holder" not in html
