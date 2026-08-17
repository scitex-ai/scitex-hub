#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""A repo READ must not consume a visitor WORKSPACE.

Card hub-visitor-slots-burned-by-scraper-botnet-20260817.

Measured on prod twice on 2026-08-17. ``VisitorAutoLoginMiddleware``
allocated a real provisioned slot (workspace + Gitea repo) for ANY
unauthenticated request whose User-Agent looked like a browser, with only
"/" and "/landing/" exempt. A crawler walking GitHub-style repo URLs
(``/visitor-014/dotfiles/blob/gitconfig``, ``/visitor-003/dotfiles/pulls/``,
``/apps/home/?project=NNNNN``) therefore held the entire pool —
``total=16 allocated=11 free=5 ready=0 ALLOCATABLE=0`` at 18:34Z — and real
humans fell through to the shared read-only account.

The measured User-Agents are spoofed Chrome strings from rotating
residential IPs, so identity cannot separate the crawl from a person.
These tests pin the fix that does not try: the exemption is by PATH — what
the page is FOR — and it is asserted against a pool that has a genuinely
allocatable slot, so "no allocation happened" means the slot was refused,
not that there was nothing to take.

Both halves are pinned here:
  * exempt paths take no slot, write no session, and still render;
  * a real anonymous person opening an APP page still gets a full
    writable slot, exactly as before.

Real DB, real ``RequestFactory``/``Client``, real ``VisitorPool`` — no
mocks (STX-NM001/003). AAA markers, one assertion per test (STX-TQ002/007).
"""

import shutil
from datetime import timedelta
from importlib import import_module
from pathlib import Path

from django.conf import settings
from django.contrib.auth.models import AnonymousUser, User
from django.test import Client, RequestFactory, TestCase
from django.utils import timezone

from apps.infra.project_app.middleware import VisitorAutoLoginMiddleware
from apps.infra.project_app.models import Project, VisitorAllocation
from apps.infra.project_app.services.project_filesystem import (
    get_project_filesystem_manager,
)
from apps.infra.project_app.services.visitor_pool import VisitorPool
from apps.infra.project_app.services.visitor_pool.workspace_manager import (
    TEMPLATE_MARKER_RELPATH,
)
from apps.infra.project_app.visitor_browse_paths import (
    is_hub_project_enumeration,
    is_repo_browse_path,
    needs_no_visitor_workspace,
)

# A spoofed-Chrome User-Agent — byte-for-byte the shape the crawl sends and
# the shape a real person sends. Every test below uses THIS ONE string, so
# nothing here can accidentally pass by sniffing the agent.
BROWSER_UA = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
)

# Paths lifted verbatim from the prod access log (18:34Z), plus the two
# route shapes the URLconf declares that the log sample did not happen to
# contain (``/commit/<hash>/``, ``/compare/<rev>/``).
CRAWLED_BROWSE_PATHS = (
    "/visitor-014/dotfiles/blob/gitconfig",
    "/visitor-006/dotfiles/commits/main/bashrc",
    "/visitor-002/dotfiles/blob/.git/info/exclude",
    "/visitor-013/dotfiles/blob/.gitignore",
    "/visitor-003/dotfiles/pulls/",
    "/visitor-014/dotfiles/issues/",
    "/visitor-009/dotfiles/commit/deadbeef/",
    "/visitor-009/dotfiles/compare/main...topic/",
    "/visitor-009/dotfiles/pull/42/",
    "/visitor-009/dotfiles/raw/README.md",
)

_SessionStore = import_module(settings.SESSION_ENGINE).SessionStore


def _noop_get_response(request):  # pragma: no cover - never invoked here
    return None


class RepoBrowsePathClassificationTest(TestCase):
    """The predicate matches the REAL route shapes, and nothing wider."""

    def test_blob_path_is_repo_browse(self):
        # Arrange
        path = "/visitor-014/dotfiles/blob/gitconfig"
        # Act
        matched = is_repo_browse_path(path)
        # Assert
        assert matched is True

    def test_commits_path_is_repo_browse(self):
        # Arrange
        path = "/visitor-006/dotfiles/commits/main/bashrc"
        # Act
        matched = is_repo_browse_path(path)
        # Assert
        assert matched is True

    def test_pulls_path_is_repo_browse(self):
        # Arrange
        path = "/visitor-003/dotfiles/pulls/"
        # Act
        matched = is_repo_browse_path(path)
        # Assert
        assert matched is True

    def test_issues_path_is_repo_browse(self):
        # Arrange
        path = "/visitor-014/dotfiles/issues/"
        # Act
        matched = is_repo_browse_path(path)
        # Assert
        assert matched is True

    def test_repository_root_is_not_repo_browse(self):
        # Arrange: the repo root carries no browse verb — it keeps allocating.
        path = "/visitor-014/dotfiles/"
        # Act
        matched = is_repo_browse_path(path)
        # Assert
        assert matched is False

    def test_app_page_is_not_repo_browse(self):
        # Arrange: an app page is ALSO a two-segment path. Matching the
        # repository URLconf's <path:directory_path>/ catch-all here would
        # have swallowed it and broken every real visitor.
        path = "/apps/figrecipe/"
        # Act
        matched = is_repo_browse_path(path)
        # Assert
        assert matched is False

    def test_verb_as_repo_name_is_not_repo_browse(self):
        # Arrange: the verb must be the THIRD segment, not the second.
        path = "/ywatanabe/issues/"
        # Act
        matched = is_repo_browse_path(path)
        # Assert
        assert matched is False

    def test_numeric_project_query_is_enumeration(self):
        # Arrange
        query = {"project": "31337"}
        # Act
        matched = is_hub_project_enumeration("/apps/home/", query)
        # Assert
        assert matched is True

    def test_bare_hub_index_is_not_enumeration(self):
        # Arrange: the hero CTA target — the one deliberate "enter the
        # workspace" click, which MUST keep allocating.
        query = {}
        # Act
        matched = is_hub_project_enumeration("/apps/home/", query)
        # Assert
        assert matched is False

    def test_non_numeric_project_query_is_not_enumeration(self):
        # Arrange
        query = {"project": "my-paper"}
        # Act
        matched = is_hub_project_enumeration("/apps/home/", query)
        # Assert
        assert matched is False

    def test_post_to_browse_path_is_not_exempt(self):
        # Arrange: only READS are exempt; commenting on an issue is a
        # genuine interaction and still deserves a workspace.
        request = RequestFactory().post(
            "/visitor-014/dotfiles/issues/", HTTP_USER_AGENT=BROWSER_UA
        )
        # Act
        exempt = needs_no_visitor_workspace(request)
        # Assert
        assert exempt is False

    def test_raw_mode_query_does_not_change_classification(self):
        # Arrange: there is no /raw/ route — raw is /blob/<path>?mode=raw.
        request = RequestFactory().get(
            "/visitor-013/dotfiles/blob/.gitignore",
            {"mode": "raw"},
            HTTP_USER_AGENT=BROWSER_UA,
        )
        # Act
        exempt = needs_no_visitor_workspace(request)
        # Assert
        assert exempt is True


class _AllocatablePoolTestCase(TestCase):
    """Base fixture: ONE genuinely allocatable slot, plus readonly-visitor.

    Without a distributable slot every assertion below would be vacuous —
    "no allocation happened" would just mean there was nothing to allocate.
    The slot is built the way ``pool_manager`` demands: a visitor-001
    user + default-project, a reconciled ``VisitorAllocation`` row that is
    inactive/expired/``workspace_ready``, and the on-disk template marker
    the synchronous pre-handoff check verifies.
    """

    def setUp(self):
        self.readonly_visitor = User.objects.create_user(
            username=VisitorPool.READONLY_VISITOR_USERNAME,
            password="TestPass123!",  # pragma: allowlist secret
        )
        self.visitor_user, _ = User.objects.get_or_create(
            username="visitor-001", defaults={"email": "v001@example.com"}
        )
        self.visitor_project, _ = Project.objects.get_or_create(
            slug="default-project",
            owner=self.visitor_user,
            defaults={"name": "Default Project"},
        )
        now = timezone.now()
        VisitorAllocation.objects.filter(visitor_number=1).delete()
        VisitorAllocation.objects.create(
            visitor_number=1,
            session_key="",
            allocation_token="pool-slot-1",  # pragma: allowlist secret
            expires_at=now - timedelta(minutes=60),
            is_active=False,
            last_activity=now - timedelta(days=3),
            workspace_ready=True,
            quarantined=False,
        )
        manager = get_project_filesystem_manager(self.visitor_user)
        marker = (
            Path(manager.base_path)
            / self.visitor_project.slug
            / TEMPLATE_MARKER_RELPATH
        )
        marker.mkdir(parents=True, exist_ok=True)
        (marker / "config.yaml").write_text("template: true\n")

    def tearDown(self):
        base = Path(settings.BASE_DIR) / "data" / "users" / "visitor-001"
        if base.exists():
            shutil.rmtree(base, ignore_errors=True)

    def run_middleware(self, path, data=None):
        request = RequestFactory().get(path, data or {}, HTTP_USER_AGENT=BROWSER_UA)
        request.user = AnonymousUser()
        request.session = _SessionStore()
        VisitorAutoLoginMiddleware(_noop_get_response)._sync_body(request)
        return request

    @staticmethod
    def live_allocations():
        return VisitorAllocation.objects.filter(is_active=True).count()


class PoolIsGenuinelyAllocatableTest(_AllocatablePoolTestCase):
    """Guard for every test below: the fixture really can hand out a slot."""

    def test_an_app_page_takes_the_slot(self):
        # Arrange: a real anonymous person opening an app page.
        path = "/apps/figrecipe/"
        # Act
        self.run_middleware(path)
        # Assert — if this ever reads 0, every "no allocation" below is vacuous.
        assert self.live_allocations() == 1


class BrowseExemptionTakesNoSlotTest(_AllocatablePoolTestCase):
    """The crawled shapes leave the allocatable slot untouched."""

    def test_crawled_browse_paths_allocate_nothing(self):
        # Arrange: the full set of shapes measured in the prod access log.
        paths = CRAWLED_BROWSE_PATHS
        # Act
        for path in paths:
            with self.subTest(path=path):
                self.run_middleware(path)
        # Assert — one shared slot, ten crawl hits, zero taken.
        assert self.live_allocations() == 0

    def test_raw_mode_variant_allocates_nothing(self):
        # Arrange
        path = "/visitor-013/dotfiles/blob/.gitignore"
        # Act
        self.run_middleware(path, {"mode": "raw"})
        # Assert
        assert self.live_allocations() == 0

    def test_hub_project_enumeration_allocates_nothing(self):
        # Arrange: the sequential /apps/home/?project=NNNNN walk.
        path = "/apps/home/"
        # Act
        self.run_middleware(path, {"project": "31337"})
        # Assert
        assert self.live_allocations() == 0

    def test_browse_request_gets_the_shared_readonly_identity(self):
        # Arrange: the page must still have someone to render AS.
        path = "/visitor-014/dotfiles/blob/gitconfig"
        # Act
        request = self.run_middleware(path)
        # Assert
        assert request.user.username == VisitorPool.READONLY_VISITOR_USERNAME

    def test_browse_request_writes_nothing_to_the_session(self):
        # Arrange: no login() means no session row and no cookie, so a
        # cookie-less crawl costs storage as well as slots: nothing.
        path = "/visitor-014/dotfiles/blob/gitconfig"
        # Act
        request = self.run_middleware(path)
        # Assert
        assert dict(request.session) == {}

    def test_browse_request_sets_no_readonly_downgrade_notice(self):
        # Arrange: nothing was DOWNGRADED here, so telling this reader that
        # "all visitor slots are in use" would be a lie.
        path = "/visitor-003/dotfiles/pulls/"
        # Act
        request = self.run_middleware(path)
        # Assert
        assert request.session.get("is_readonly_visitor") is None

    def test_browse_then_app_page_still_gets_a_writable_slot(self):
        # Arrange: a real person who arrived on a shared repo link first.
        self.run_middleware("/visitor-014/dotfiles/blob/gitconfig")
        # Act: then they open an app.
        request = self.run_middleware("/apps/figrecipe/")
        # Assert — the link they followed does not pin them read-only.
        assert request.user.username == "visitor-001"


class AppPagesStillAllocateTest(_AllocatablePoolTestCase):
    """Regression guard: normal visitor entry is untouched by the exemption."""

    def test_app_page_logs_in_a_pool_visitor(self):
        # Arrange
        path = "/apps/figrecipe/"
        # Act
        request = self.run_middleware(path)
        # Assert
        assert request.user.username == "visitor-001"

    def test_writer_app_page_logs_in_a_pool_visitor(self):
        # Arrange
        path = "/apps/writer/"
        # Act
        request = self.run_middleware(path)
        # Assert
        assert request.user.username == "visitor-001"

    def test_hero_cta_hub_index_still_allocates(self):
        # Arrange: bare /apps/home/, no ?project=, is the hero CTA.
        path = "/apps/home/"
        # Act
        self.run_middleware(path)
        # Assert
        assert self.live_allocations() == 1

    def test_authenticated_user_browsing_a_repo_is_untouched(self):
        # Arrange: the middleware only ever acts on anonymous requests.
        signed_in = User.objects.create_user(
            username="ywatanabe",
            password="TestPass123!",  # pragma: allowlist secret
        )
        request = RequestFactory().get(
            "/ywatanabe/paper/blob/README.md", HTTP_USER_AGENT=BROWSER_UA
        )
        request.user = signed_in
        request.session = _SessionStore()
        # Act
        VisitorAutoLoginMiddleware(_noop_get_response)._sync_body(request)
        # Assert
        assert request.user.username == "ywatanabe"


class ExemptPathStillRendersTest(_AllocatablePoolTestCase):
    """An exempted path must RENDER — not 500, not bounce to pool-full."""

    def setUp(self):
        super().setUp()
        self.owner = User.objects.create_user(
            username="ywatanabe",
            password="TestPass123!",  # pragma: allowlist secret
        )
        self.public_project = Project.objects.create(
            slug="paper",
            owner=self.owner,
            name="Paper",
            visibility="public",
        )
        self.client = Client(HTTP_USER_AGENT=BROWSER_UA)

    def test_public_repo_issues_page_renders(self):
        # Arrange: a real end-to-end GET through the whole middleware chain,
        # on a public repo, with no cookie.
        url = "/ywatanabe/paper/issues/"
        # Act
        response = self.client.get(url)
        # Assert
        assert response.status_code == 200

    def test_hub_enumeration_does_not_bounce_to_pool_full(self):
        # Arrange: index_view redirects a logged-out browser to
        # /visitor-pool-full/; the shared read-only identity keeps the
        # exempted request out of that bounce.
        url = "/apps/home/"
        # Act
        response = self.client.get(url, {"project": "31337"})
        # Assert
        assert response.status_code == 200

    def test_exempt_render_still_allocates_nothing(self):
        # Arrange
        url = "/ywatanabe/paper/issues/"
        # Act
        self.client.get(url)
        # Assert
        assert self.live_allocations() == 0


# EOF
