#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for the path-containment primitive.

These are adversarial on purpose: the whole value of `resolve_within` is that
it says NO to inputs that a hand-written guard says yes to, so most of the
cases below are escapes that must be rejected. A test file that only proves
the happy path would pass against the buggy hand-written version this module
replaces.
"""

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from apps.infra.platform_app.services.paths import resolve_within


class ResolveWithinTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name) / "proj"
        (self.root / "sub").mkdir(parents=True)
        (self.root / "sub" / "file.txt").write_text("ok")
        self.outside = Path(self._tmp.name) / "outside"
        self.outside.mkdir()
        (self.outside / "secret.txt").write_text("secret")

    def tearDown(self):
        self._tmp.cleanup()

    # ---- allowed ----------------------------------------------------------

    def test_empty_fragment_is_the_root_itself(self):
        self.assertEqual(resolve_within(self.root, ""), self.root.resolve())

    def test_none_fragment_is_the_root_itself(self):
        self.assertEqual(resolve_within(self.root, None), self.root.resolve())

    def test_simple_child(self):
        self.assertEqual(
            resolve_within(self.root, "sub/file.txt"),
            (self.root / "sub" / "file.txt").resolve(),
        )

    def test_leading_slash_is_treated_as_relative_not_absolute(self):
        # Path("/root") / "/etc/passwd" == Path("/etc/passwd"): pathlib DISCARDS
        # the left side. The leading slash must not smuggle an absolute path in.
        self.assertEqual(
            resolve_within(self.root, "/sub/file.txt"),
            (self.root / "sub" / "file.txt").resolve(),
        )

    def test_interior_dotdot_that_stays_inside_is_allowed(self):
        self.assertEqual(
            resolve_within(self.root, "sub/../sub/file.txt"),
            (self.root / "sub" / "file.txt").resolve(),
        )

    def test_nonexistent_but_contained_path_is_allowed(self):
        # Containment is NOT existence. Returning a path here is correct; the
        # caller checks existence afterwards. Conflating the two is the bug
        # this module exists to prevent.
        self.assertEqual(
            resolve_within(self.root, "sub/nope.txt"),
            (self.root / "sub" / "nope.txt").resolve(),
        )

    # ---- rejected ---------------------------------------------------------

    def test_dotdot_escape_is_rejected(self):
        self.assertIsNone(resolve_within(self.root, "../outside/secret.txt"))

    def test_deep_dotdot_escape_is_rejected(self):
        self.assertIsNone(resolve_within(self.root, "sub/../../outside/secret.txt"))

    def test_absolute_looking_input_is_reinterpreted_as_relative_not_honoured(self):
        # An absolute-looking fragment is NOT honoured as absolute and is NOT
        # rejected either: the leading "/" is stripped, so it becomes a walk
        # under the root. "/etc/passwd" therefore names <root>/etc/passwd --
        # harmless -- and can never name the real /etc/passwd.
        #
        # This is deliberate, and it is what the callers already did by hand
        # (api_browse.py did .strip("/") on the query parameter): a UI that
        # builds "/sub/file.txt" must keep working. The security property that
        # matters is that the result is inside the root, which is asserted here.
        got = resolve_within(self.root, "/etc/passwd")
        self.assertEqual(got, (self.root / "etc" / "passwd").resolve())
        self.assertNotEqual(got, Path("/etc/passwd"))
        self.assertTrue(got.is_relative_to(self.root.resolve()))

    def test_absolute_path_with_traversal_still_cannot_escape(self):
        # Stripping the slash must not become a bypass: an absolute-looking
        # fragment that ALSO walks up has to be rejected like any other escape.
        self.assertIsNone(resolve_within(self.root, "/../outside/secret.txt"))

    def test_symlink_pointing_outside_is_rejected(self):
        link = self.root / "escape"
        try:
            link.symlink_to(self.outside)
        except (OSError, NotImplementedError):
            self.skipTest("symlinks unavailable on this platform")
        self.assertIsNone(resolve_within(self.root, "escape/secret.txt"))

    def test_nul_byte_is_rejected(self):
        # NUL truncates the string at the syscall boundary, so a path validated
        # with the suffix present could reach the OS as a different path.
        self.assertIsNone(resolve_within(self.root, "sub/file.txt\x00.png"))

    def test_none_root_is_rejected(self):
        self.assertIsNone(resolve_within(None, "anything"))

    def test_sibling_prefix_is_not_treated_as_inside(self):
        # "/tmp/x/proj-evil" starts with "/tmp/x/proj" as a STRING but is not
        # inside it. A guard written with startswith() gets this wrong.
        sibling = self.root.parent / (self.root.name + "-evil")
        sibling.mkdir()
        (sibling / "secret.txt").write_text("secret")
        self.assertIsNone(
            resolve_within(self.root, "../" + sibling.name + "/secret.txt")
        )

    def test_does_not_raise_on_symlink_loop(self):
        a = self.root / "loop_a"
        b = self.root / "loop_b"
        try:
            a.symlink_to(b)
            b.symlink_to(a)
        except (OSError, NotImplementedError):
            self.skipTest("symlinks unavailable on this platform")
        # Must return a verdict, not blow up in the caller's request handler.
        self.assertIsNone(resolve_within(self.root, "loop_a/x"))

    def test_rejection_is_indistinguishable_for_existing_and_missing_targets(self):
        # Both are outside the root. If one returned something different from
        # the other, the caller could tell whether a file it may not read
        # exists -- the exact oracle this module removes.
        self.assertEqual(
            resolve_within(self.root, "../outside/secret.txt"),
            resolve_within(self.root, "../outside/does-not-exist.txt"),
        )


if __name__ == "__main__":  # pragma: no cover
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.settings_dev")
    unittest.main()
