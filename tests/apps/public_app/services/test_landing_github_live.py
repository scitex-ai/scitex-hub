"""Owned in-memory quota/cache and real Django endpoint controls, without a DB."""

from __future__ import annotations

import unittest
from threading import Event
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

from django.conf import settings

if not settings.configured:
    settings.configure(USE_I18N=False, SECRET_KEY="owned-cache-fixture")
from django.core.cache.backends.locmem import LocMemCache
from django.test import RequestFactory, override_settings

from apps.infra.public_app.services.landing_github import REPOSITORIES
from apps.infra.public_app.services.landing_github_live import (
    CACHE_KEY,
    LAST_GOOD_KEY,
    cached_counts,
    fetch_official_counts,
)
from apps.infra.public_app.api_github import github_counts


def owned_result():
    return {
        "status": "fresh",
        "fetched_at": "2026-11-03T00:00:00+00:00",
        "repositories": {
            name: {"available": True, "stars": 7, "forks": 3} for name in REPOSITORIES
        },
    }


class LiveCountsTests(unittest.TestCase):
    def setUp(self):
        self.cache = LocMemCache("owned-github-" + uuid4().hex, {})

    def test_second_request_uses_cached_public_result_without_refetch(self):
        # Arrange
        calls = []

        def fetch():
            calls.append(True)
            return owned_result()

        # Act
        first = cached_counts(self.cache, fetcher=fetch)
        second = cached_counts(self.cache, fetcher=fetch)
        # Assert
        self.assertEqual(
            (first, second, len(calls)), (owned_result(), owned_result(), 1)
        )

    def test_upstream_failure_keeps_last_good_and_cools_down_following_requests(self):
        # Arrange
        self.cache.set(LAST_GOOD_KEY, owned_result(), 60)
        calls = []

        def unavailable():
            calls.append(True)
            raise OSError("owned unavailable upstream")

        # Act
        first = cached_counts(self.cache, fetcher=unavailable)
        second = cached_counts(self.cache, fetcher=unavailable)
        # Assert
        self.assertEqual(
            (first["status"], second["repositories"], len(calls)),
            ("stale", owned_result()["repositories"], 1),
        )

    def test_concurrent_visitor_does_not_start_a_second_upstream_fetch(self):
        # Arrange
        entered, release = Event(), Event()
        calls = []

        def fetch():
            calls.append(True)
            entered.set()
            if not release.wait(5):
                raise TimeoutError("owned fixture release missing")
            return owned_result()

        # Act
        with ThreadPoolExecutor(max_workers=1) as pool:
            owner = pool.submit(cached_counts, self.cache, fetcher=fetch)
            if not entered.wait(5):
                self.fail("owner did not enter upstream")
            visitor = cached_counts(self.cache, fetcher=fetch)
            release.set()
            first = owner.result(timeout=5)
        # Assert
        self.assertEqual(
            (len(calls), first["status"], visitor["status"]), (1, "fresh", "snapshot")
        )

    def test_get_only_endpoint_ignores_force_and_foreign_repository_selectors(self):
        # Arrange
        config = {
            "default": {
                "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
                "LOCATION": "owned-view-" + uuid4().hex,
            }
        }
        with override_settings(CACHES=config):
            from django.core.cache import caches

            caches["default"].set(CACHE_KEY, owned_result(), 60)
            request = RequestFactory().get(
                "/api/landing/github-counts/?force=1&repo=private/other"
            )
            # Act
            result = github_counts(request)
            import json

            observed = (result.status_code, json.loads(result.content))
        # Assert
        self.assertEqual(observed, (200, owned_result()))

    def test_post_is_refused_without_fetching_or_writing(self):
        # Arrange
        request = RequestFactory().post("/api/landing/github-counts/", {})
        # Act
        result = github_counts(request)
        # Assert
        self.assertEqual(result.status_code, 405)

    def test_disabled_cache_uses_snapshot_without_network(self):
        # Arrange
        config = {"default": {"BACKEND": "django.core.cache.backends.dummy.DummyCache"}}
        # Act
        with override_settings(CACHES=config):
            import json

            result = json.loads(
                github_counts(
                    RequestFactory().get("/api/landing/github-counts/")
                ).content
            )
        # Assert
        self.assertEqual(
            (result["status"], set(result["repositories"])),
            ("snapshot", set(REPOSITORIES)),
        )


if __name__ == "__main__":
    unittest.main()
