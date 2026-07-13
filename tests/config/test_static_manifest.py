#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""collectstatic must SUCCEED under the content-hashing storage backend.

This test is a production gate, not a nicety.

settings_static.py switches staticfiles to WhiteNoise's
CompressedManifestStaticFilesStorage so that {% static %} emits content-hashed
URLs (see the note there: un-hashed URLs + Cloudflare's 30-day browser TTL is
what let a phone render the launcher with month-old CSS and fresh JS).

That backend POST-PROCESSES every collected CSS file, rewriting each url() and
@import to the hashed name of its target — and it RAISES if a target does not
exist. hub's production entrypoint runs `collectstatic` at boot under `set -e`,
so a single dangling reference anywhere in the tree is not a broken image: it is
a container that never starts. Exactly the shape of the 2026-07-11 outage.

So: fail here, in CI, where it is free.
"""

import tempfile
from pathlib import Path

from django.conf import settings
from django.core.management import call_command
from django.test import override_settings

from config.settings.settings_static import hashed_storages


def test_collectstatic_succeeds_with_hashed_urls():
    # Arrange: collect into a throwaway root so the test never touches the real
    # staticfiles/ (which the dev server and the Vite build both read).
    #
    # This test opts INTO the hashing backend explicitly. It is not the global
    # default: the manifest backend reads staticfiles.json, which only exists
    # after collectstatic has run, so making it global would make every OTHER
    # test's page render raise "Missing staticfiles manifest entry". Only
    # prod/staging — whose entrypoint runs collectstatic at boot — enable it.
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)

        # Act: the real management command against the real prod backend. If any
        # CSS url()/@import points at a file that does not exist, this raises
        # ValueError and the test fails — which is the entire point.
        with override_settings(
            STATIC_ROOT=str(root),
            STORAGES=hashed_storages(settings.STORAGES),
        ):
            call_command("collectstatic", interactive=False, verbosity=0)

        # Assert: the manifest exists, which is the artefact {% static %} reads
        # at render time to turn a name into its hashed URL. No manifest means
        # every template render would 500 in production.
        assert (root / "staticfiles.json").exists()


# EOF
