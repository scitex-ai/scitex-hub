#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for the package-layout user library (scitex-scholar thin layer)."""

from django.contrib.auth.models import User
from django.test import TestCase, override_settings

from apps.workspace.scholar_app.services.user_library_service import (
    UserLibraryService,
    _paper_id,
)


class TestPaperId(TestCase):
    def test_doi_safe(self):
        self.assertEqual(
            _paper_id("10.1000/xyz:123", "doi"), "doi-10.1000_xyz_123"
        )

    def test_fallback(self):
        self.assertEqual(_paper_id("", ""), "unknown")


class TestPackageLayout(TestCase):
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

    def test_flat_metadata_folds_into_sections(self):
        import json
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as tmp:
            svc = self._service(Path(tmp))
            result = svc.add_paper(
                identifier="10.1000/flat",
                id_type="doi",
                bibtex_content="@article{flat, title={Flat}}",
                metadata={"title": "Flat Paper", "year": 2023},
            )
            meta = json.loads(
                (svc.library_path / result["bibtex"]).parent
                .joinpath("metadata.json").read_text()
            )["metadata"]
            self.assertEqual(meta["basic"]["title"], "Flat Paper")
            self.assertEqual(meta["basic"]["year"], 2023)
            self.assertEqual(meta["id"]["doi"], "10.1000/flat")

    def test_master_created_no_legacy_dirs(self):
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as tmp:
            svc = self._service(Path(tmp))
            self.assertTrue((svc.library_path / "MASTER").is_dir())
            for legacy in ("collections", "metadata"):
                self.assertFalse((svc.library_path / legacy).exists())
            self.assertFalse((svc.library_path / "papers").exists())

    def test_add_paper_master_with_metadata(self):
        import json
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as tmp:
            svc = self._service(Path(tmp))
            result = svc.add_paper(
                identifier="10.1000/demo",
                id_type="doi",
                bibtex_content="@article{demo, title={Demo}}",
                metadata={
                    "basic": {"title": "Demo Paper", "year": 2024},
                    "publication": {"journal": "J Demo"},
                },
            )
            rel_pdf = result.get("pdf")
            rel_bib = result.get("bibtex")
            self.assertIsNone(rel_pdf)  # no PDF given
            self.assertTrue(str(rel_bib).startswith("MASTER/"))
            meta = json.loads(
                (svc.library_path / rel_bib).parent.joinpath(
                    "metadata.json"
                ).read_text()
            )
            self.assertEqual(meta["metadata"]["id"]["doi"], "10.1000/demo")
            self.assertEqual(meta["metadata"]["basic"]["title"], "Demo Paper")
            self.assertEqual(meta["metadata"]["publication"]["journal"], "J Demo")
            # get_paper_path resolves the MASTER bib
            found = svc.get_paper_path("10.1000/demo", "doi", "bib")
            self.assertIsNotNone(found)
            self.assertTrue(found.name.endswith(".bib"))

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
