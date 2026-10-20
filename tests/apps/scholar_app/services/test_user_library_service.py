#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for the thin hub wrapper (path resolution + project links).

Storage behavior (MASTER writes, metadata schema, legacy fallbacks) is
owned and tested by the leaf (scitex-scholar ``storage._master_store``).
What is tested here is only what the hub adds: whose library a user maps
to, and the project tree link lifecycle.
"""

from django.contrib.auth.models import User
from django.test import TestCase, override_settings

from apps.workspace.scholar_app.services.user_library_service import (
    UserLibraryService,
)


class TestThinWrapper(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="libtest-no-unix-user-xyz")

    def _service(self, tmp_root):
        with override_settings(
            USER_DATA_ROOT=tmp_root,
            SCITEX_SCHOLAR_USER_LIBRARY_ROOT=tmp_root / "fallback",
        ):
            return UserLibraryService(self.user)

    def test_users_root_not_doubled(self):
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as tmp:
            # Deployment points USER_DATA_ROOT straight at the users tree.
            svc = self._service(Path(tmp) / "users")
            self.assertEqual(
                svc.library_path,
                Path(tmp) / "users" / self.user.username
                / ".scitex" / "scholar" / "library",
            )
            self.assertNotIn("users/users", str(svc.library_path))

    def test_add_delegates_to_leaf_master(self):
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as tmp:
            svc = self._service(Path(tmp))
            result = svc.add_paper(
                identifier="10.1000/demo",
                id_type="doi",
                bibtex_content="@article{demo, title={Demo}}",
                metadata={"basic": {"title": "Demo Paper", "year": 2024}},
            )
            self.assertTrue(str(result["bibtex"]).startswith("MASTER/"))
            self.assertTrue((svc.library_path / result["bibtex"]).exists())
            found = svc.get_paper_path("10.1000/demo", "doi", "bib")
            self.assertIsNotNone(found)

    def test_project_link_roundtrip(self):
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as tmp:
            svc = self._service(Path(tmp))
            proj = Path(tmp) / "proj"
            proj.mkdir()
            link = svc.ensure_project_link(proj)
            self.assertTrue(link.is_symlink())
            self.assertEqual(
                link.readlink(), svc.library_path.resolve()
            )
            # idempotent
            self.assertEqual(svc.ensure_project_link(proj), link)
            self.assertTrue(svc.prune_project_link(proj))
            self.assertFalse(link.exists() or link.is_symlink())

    def test_empty_placeholder_dir_adopted(self):
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as tmp:
            svc = self._service(Path(tmp))
            placeholder = Path(tmp) / "proj" / ".scitex" / "scholar" / "library"
            placeholder.mkdir(parents=True)
            link = svc.ensure_project_link(Path(tmp) / "proj")
            self.assertTrue(link.is_symlink())
            self.assertEqual(link.readlink(), svc.library_path.resolve())

    def test_nonempty_dir_refused(self):
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as tmp:
            svc = self._service(Path(tmp))
            occupied = Path(tmp) / "proj" / ".scitex" / "scholar" / "library"
            occupied.mkdir(parents=True)
            (occupied / "keep.txt").write_text("data")
            with self.assertRaises(FileExistsError):
                svc.ensure_project_link(Path(tmp) / "proj")
