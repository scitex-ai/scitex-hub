"""Real local snapshot/template contracts; no database or remote requests."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from apps.infra.public_app.services.landing_github import (
    API_ROOT,
    REPOSITORIES,
    SNAPSHOT,
    repository_cards,
    validate_repository,
)
from apps.infra.public_app.services.refresh_landing_github import (
    _NoRedirect,
    refresh_snapshot,
    write_snapshot,
)

ROOT = Path(__file__).resolve().parents[4]


def snapshot_record(**changes):
    """Owned public metadata fixture, including genuine zero counts."""
    record = {
        "full_name": "scitex-ai/scitex-sdk",
        "private": False,
        "stargazers_count": 0,
        "forks_count": 2,
        "description": "<script>literal metadata</script>",
    }
    record.update(changes)
    return record


class RepositoryMetadataTests(unittest.TestCase):
    def test_official_response_reduces_to_counts_and_public_fields(self):
        # Arrange
        source = snapshot_record(unneeded_private_field="must-not-ship")
        # Act
        actual = validate_repository("scitex-sdk", source)
        # Assert
        self.assertEqual(
            actual,
            {
                "available": True,
                "stars": 0,
                "forks": 2,
                "description": "<script>literal metadata</script>",
                "source": API_ROOT + "scitex-sdk",
            },
        )

    def test_invalid_counts_and_foreign_or_private_repository_are_refused(self):
        # Arrange
        cases = [
            {"full_name": "another/repo"},
            {"private": True},
            {"stargazers_count": True},
            {"forks_count": -1},
            {"forks_count": "2"},
            {"description": []},
        ]
        # Act
        refused = []
        for values in cases:
            try:
                validate_repository("scitex-sdk", snapshot_record(**values))
            except ValueError:
                refused.append(values)
        # Assert
        self.assertEqual(refused, cases)

    def test_missing_snapshot_has_no_fabricated_zero_counts_or_writes(self):
        # Arrange
        with tempfile.TemporaryDirectory() as directory:
            missing = Path(directory) / "missing.json"
            # Act
            result = repository_cards(missing)
            observation = (
                missing.exists(),
                [r["stars"] for g in result["groups"] for r in g["cards"]],
            )
        # Assert
        self.assertEqual(observation, (False, [None] * len(REPOSITORIES)))

    def test_replaced_snapshot_refreshes_cached_counts_and_unavailable_stays_explicit(
        self,
    ):
        # Arrange
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "snapshot.json"
            data = {
                "schema": 1,
                "checked_at": "2026-11-02T21:03:05+00:00",
                "repositories": {},
            }
            write_snapshot(data, target)
            before = repository_cards(target)
            data["repositories"]["scitex-sdk"] = validate_repository(
                "scitex-sdk", snapshot_record()
            )
            # Act
            write_snapshot(data, target)
            after = repository_cards(target)
            sdk = next(
                r
                for g in after["groups"]
                for r in g["cards"]
                if r["name"] == "scitex-sdk"
            )
        # Assert
        self.assertEqual(
            (
                all(not r["available"] for g in before["groups"] for r in g["cards"]),
                sdk["stars"],
                sdk["forks"],
            ),
            (True, 0, 2),
        )

    def test_corrupt_and_undated_snapshot_never_exposes_unattributed_counts(self):
        # Arrange
        sources = ["not JSON", "[]", '{"schema":1,"checked_at":"tomorrow"}']
        # Act
        unavailable = []
        with tempfile.TemporaryDirectory() as directory:
            for index, raw in enumerate(sources):
                target = Path(directory) / f"snapshot{index}.json"
                target.write_text(raw)
                unavailable.append(
                    all(
                        not r["available"]
                        for g in repository_cards(target)["groups"]
                        for r in g["cards"]
                    )
                )
        # Assert
        self.assertEqual(unavailable, [True] * len(sources))

    def test_nonpositive_nonfinite_request_bounds_are_refused_before_network(self):
        # Arrange
        bounds = [0, -1, float("nan"), float("inf")]
        # Act
        refused = []
        for bound in bounds:
            try:
                refresh_snapshot(timeout=bound)
            except ValueError:
                refused.append(True)
        # Assert
        self.assertEqual(refused, [True] * len(bounds))

    def test_expired_batch_budget_performs_no_network_and_returns_unavailable(self):
        # Arrange
        program = """import json,sys
attempts=[]
def observe(event,args):
 if event=='socket.connect':attempts.append(event);raise RuntimeError('network refused')
sys.addaudithook(observe)
from apps.infra.public_app.services.refresh_landing_github import refresh_snapshot
result=refresh_snapshot(budget=5e-324)
print(json.dumps([attempts,all(not r['available'] for r in result['repositories'].values())]))
"""
        # Act
        with tempfile.TemporaryDirectory() as directory:
            child = subprocess.run(
                [sys.executable, "-c", program],
                cwd=ROOT,
                env={"HOME": directory, "PATH": os.defpath},
                capture_output=True,
                text=True,
                timeout=10,
                check=True,
            )
        # Assert
        self.assertEqual(json.loads(child.stdout), [[], True])

    def test_api_redirect_is_not_followed(self):
        # Arrange
        policy = _NoRedirect()
        # Act
        result = policy.redirect_request(
            None, None, 302, "redirect", {}, "http://other.invalid/"
        )
        # Assert
        self.assertIsNone(result)

    def test_checked_in_snapshot_covers_every_public_catalog_repository(self):
        # Arrange
        data = json.loads(SNAPSHOT.read_text())
        # Act
        visible = {
            row["name"]
            for group in repository_cards()["groups"]
            for row in group["cards"]
        }
        observed = (set(REPOSITORIES).issubset(data["repositories"]), visible)
        # Assert
        self.assertEqual(observed, (True, set(REPOSITORIES)))


class LandingTemplateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from django.conf import settings

        if not settings.configured:
            settings.configure(
                USE_I18N=False, STATIC_URL="/static/", SECRET_KEY="owned-render-fixture"
            )
        from django.template import Engine

        cls.engine = Engine(
            dirs=[str(ROOT / "apps/infra/public_app/templates")],
            libraries={
                "i18n": "django.templatetags.i18n",
                "static": "django.templatetags.static",
                "landing_i18n": "apps.infra.public_app.templatetags.landing_i18n",
            },
        )

    def test_actual_card_partial_renders_all_links_counts_and_icons_without_network(
        self,
    ):
        # Arrange
        from django.template import Context
        from django.test import override_settings
        from django.urls import include, path
        from types import ModuleType

        routes = ModuleType("owned_landing_urls")
        routes.urlpatterns = [
            path(
                "",
                include(
                    (
                        [
                            path(
                                "open-source/", lambda request: None, name="open_source"
                            ),
                            path(
                                "api/landing/github-counts/",
                                lambda request: None,
                                name="landing-github-counts",
                            ),
                        ],
                        "public_app",
                    )
                ),
            )
        ]
        template = self.engine.get_template(
            "public_app/landing_partials/landing_opensource.html"
        )
        # Act
        with override_settings(ROOT_URLCONF=routes, USE_I18N=False):
            html = template.render(Context({}, use_l10n=False))
        # Assert
        self.assertEqual(
            (
                all(
                    "https://github.com/scitex-ai/" + name in html
                    for name in REPOSITORIES
                ),
                html.count('class="far fa-star"'),
                html.count('class="fas fa-code-branch"'),
                'id="github"' in html,
            ),
            (True, 17, 17, True),
        )

    def test_fresh_template_render_performs_no_network_or_user_home_writes(self):
        # Arrange
        program = """import json,sys
from pathlib import Path
attempts=[]
def observe(event,args):
 if event=='socket.connect':attempts.append(event);raise RuntimeError('network refused')
sys.addaudithook(observe)
from django.conf import settings
settings.configure(USE_I18N=False,ROOT_URLCONF='owned_landing_urls',SECRET_KEY='owned-render')
from django.urls import include,path
from types import ModuleType
routes=ModuleType('owned_landing_urls')
routes.urlpatterns=[path('',include(([path('open-source/',lambda request:None,name='open_source'),path('api/landing/github-counts/',lambda request:None,name='landing-github-counts')],'public_app')))]
sys.modules[routes.__name__]=routes
from django.template import Engine,Context
engine=Engine(dirs=['apps/infra/public_app/templates'],libraries={
 'i18n':'django.templatetags.i18n','static':'django.templatetags.static',
 'landing_i18n':'apps.infra.public_app.templatetags.landing_i18n'})
html=engine.get_template('public_app/landing_partials/landing_opensource.html').render(Context({},use_l10n=False))
print(json.dumps([attempts,html.count('class="far fa-star"'),list(Path.home().iterdir())]))
"""
        # Act
        with tempfile.TemporaryDirectory() as directory:
            result = subprocess.run(
                [sys.executable, "-c", program],
                cwd=ROOT,
                env={"HOME": directory, "PATH": os.defpath},
                text=True,
                capture_output=True,
                timeout=10,
                check=True,
            )
        # Assert
        self.assertEqual(json.loads(result.stdout), [[], 17, []])

    def test_actual_card_body_escapes_external_repository_descriptions(self):
        # Arrange
        from django.template import Context

        source = (
            ROOT
            / "apps/infra/public_app/templates/public_app/landing_partials/landing_opensource.html"
        ).read_text()
        card = source[
            source.index(
                "                        <li data-github-repo="
            ) : source.index("                        </li>")
        ]
        template = self.engine.from_string("{% load i18n %}" + card)
        repo = {
            "name": "scitex-sdk",
            "url": "https://github.com/scitex-ai/scitex-sdk",
            **validate_repository("scitex-sdk", snapshot_record()),
        }
        # Act
        html = template.render(Context({"repo": repo}, use_l10n=False))
        # Assert
        self.assertEqual(
            (
                "<script>literal metadata</script>" in html,
                "&lt;script&gt;literal metadata&lt;/script&gt;" in html,
            ),
            (False, True),
        )

    def test_footer_contains_visible_star_and_fork_words_in_the_shared_row(self):
        # Arrange
        from django.template import Context
        from django.utils.translation import override

        source = (
            ROOT
            / "apps/infra/public_app/templates/public_app/landing_partials/landing_opensource.html"
        ).read_text()
        card = source[
            source.index(
                "                        <li data-github-repo="
            ) : source.index("                        </li>")
        ]
        template = self.engine.from_string("{% load i18n %}" + card)
        repo = {
            "name": "scitex-sdk",
            "url": "https://github.com/scitex-ai/scitex-sdk",
            **validate_repository("scitex-sdk", snapshot_record()),
        }
        # Act
        # This assertion names English labels, independently of prior requests.
        with override("en"):
            html = template.render(Context({"repo": repo}, use_l10n=False))
        # Assert
        self.assertEqual(
            (
                "GitHub</a>" in html,
                "<span data-github-count-label>stars</span>" in html,
                "<span data-github-count-label>forks</span>" in html,
            ),
            (True, True, True),
        )

    def test_full_workflow_is_visible_and_uses_the_real_context_media_urls(self):
        # Arrange
        from django.template import Context
        from django.test import override_settings
        from django.urls import include, path
        from types import ModuleType

        routes = ModuleType("owned_landing_urls")
        routes.urlpatterns = [
            path(
                "",
                include(
                    (
                        [
                            path("demos/", lambda request: None, name="demos"),
                        ],
                        "public_app",
                    )
                ),
            )
        ]
        template = self.engine.get_template(
            "public_app/landing_partials/landing_research_demo.html"
        )
        media = "https://scitex.ai/media/videos/scitex-automated-research-demo.mp4"
        # Act
        with override_settings(ROOT_URLCONF=routes, USE_I18N=False):
            html = template.render(
                Context(
                    {
                        "research_demo_url": media,
                        "research_demo_poster_url": "/actual-demo-poster.jpg",
                    },
                    use_l10n=False,
                )
            )
        # Assert
        self.assertEqual(
            (
                media in html,
                '<div class="landing-oss-demo"' in html,
                "autoplay" in html,
                'preload="none"' in html,
                "<details" in html
                or "<summary" in html
                or "Recorded backend workflow" in html,
            ),
            (True, True, False, True, False),
        )


if __name__ == "__main__":
    unittest.main()
