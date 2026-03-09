#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test monitoring dashboard view.

Displays API health check results with lazy loading.
Tests run per-category via AJAX for real-time progress.
"""

import time
from dataclasses import dataclass, field

import requests
from django.http import JsonResponse
from django.views.generic import TemplateView


@dataclass
class TestResult:
    """Single test result."""

    name: str
    endpoint: str
    method: str
    expected_status: int
    actual_status: int
    passed: bool
    duration_ms: float
    error: str = ""
    preview_url: str = ""


@dataclass
class TestCategory:
    """Category of tests."""

    key: str
    name: str
    icon: str
    results: list = field(default_factory=list)
    passed_count: int = 0
    all_passed: bool = True

    def __post_init__(self):
        """Calculate stats after results are set."""
        self.calculate_stats()

    def calculate_stats(self):
        """Recalculate passed count and all_passed."""
        self.passed_count = sum(1 for r in self.results if r.passed)
        self.all_passed = all(r.passed for r in self.results) if self.results else True


CATEGORY_DEFS = [
    {"key": "core", "name": "Core Services", "icon": "fas fa-server"},
    {"key": "pages", "name": "Pages", "icon": "fas fa-file"},
    {"key": "modules", "name": "Modules", "icon": "fas fa-cubes"},
    {"key": "scholar-api", "name": "Scholar API", "icon": "fas fa-book"},
    {"key": "stats-api", "name": "Stats API", "icon": "fas fa-chart-bar"},
    {"key": "plot-api", "name": "Plot API", "icon": "fas fa-palette"},
    {"key": "auth-api", "name": "Auth API", "icon": "fas fa-key"},
    {"key": "web-api", "name": "Web API Docs", "icon": "fas fa-book"},
]

_CATEGORY_METHOD_MAP = {
    "core": "_test_core_services",
    "pages": "_test_pages",
    "modules": "_test_modules",
    "scholar-api": "_test_scholar_api",
    "stats-api": "_test_stats_api",
    "plot-api": "_test_plot_api",
    "auth-api": "_test_auth_api",
    "web-api": "_test_web_api_docs",
}


class TestMonitorView(TemplateView):
    """Test monitoring dashboard — renders skeleton, tests load via AJAX."""

    template_name = "dev_app/tests.html"

    def dispatch(self, request, *args, **kwargs):
        """Allow in all environments for transparency."""
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        current_category = self.kwargs.get("category")

        if current_category:
            display_categories = [
                d for d in CATEGORY_DEFS if d["key"] == current_category
            ]
        else:
            display_categories = CATEGORY_DEFS

        context.update(
            {
                "categories": CATEGORY_DEFS,
                "display_categories": display_categories,
                "current_category": current_category,
            }
        )
        return context

    def _run_test(
        self,
        name: str,
        url: str,
        method: str = "GET",
        expected_status: int = 200,
        json_data: dict = None,
        allow_redirects: bool = False,
        preview_url: str = "",
    ) -> TestResult:
        """Run a single test and return result."""
        start = time.time()
        timeout = 2  # Reduced from 5s to fail fast and prevent blocking
        try:
            if method == "GET":
                resp = requests.get(
                    url, timeout=timeout, allow_redirects=allow_redirects
                )
            else:
                resp = requests.post(
                    url,
                    json=json_data,
                    timeout=timeout,
                    allow_redirects=allow_redirects,
                )

            duration_ms = (time.time() - start) * 1000
            passed = resp.status_code == expected_status

            return TestResult(
                name=name,
                endpoint=url.replace("http://localhost:8000", ""),
                method=method,
                expected_status=expected_status,
                actual_status=resp.status_code,
                passed=passed,
                duration_ms=round(duration_ms, 1),
                preview_url=preview_url,
            )
        except Exception as e:
            duration_ms = (time.time() - start) * 1000
            return TestResult(
                name=name,
                endpoint=url.replace("http://localhost:8000", ""),
                method=method,
                expected_status=expected_status,
                actual_status=0,
                passed=False,
                duration_ms=round(duration_ms, 1),
                error=str(e),
                preview_url=preview_url,
            )

    def _test_core_services(self, base_url: str) -> list[TestResult]:
        """Test core service endpoints."""
        return [
            self._run_test(
                "Health check (/healthz/)",
                f"{base_url}/healthz/",
                expected_status=200,
            ),
            self._run_test(
                "Server health API",
                f"{base_url}/api/server-health/",
                expected_status=200,
            ),
            self._run_test(
                "Landing page",
                f"{base_url}/",
                expected_status=200,
            ),
        ]

    def _test_pages(self, base_url: str) -> list[TestResult]:
        """Test key pages are accessible."""
        return [
            self._run_test(
                "Login page",
                f"{base_url}/auth/login/",
                expected_status=200,
            ),
            self._run_test(
                "Server status page",
                f"{base_url}/server-status/",
                expected_status=200,
            ),
        ]

    def _test_modules(self, base_url: str) -> list[TestResult]:
        """Test module index pages."""
        results = []
        modules = [
            ("Scholar", "/scholar/"),
            ("Writer", "/writer/"),
            ("Code", "/console/"),
            ("Vis", "/vis/"),
        ]
        for name, path in modules:
            results.append(
                self._run_test(
                    f"{name} module",
                    f"{base_url}{path}",
                    expected_status=200,
                    allow_redirects=True,
                )
            )
        return results

    def _test_scholar_api(self, base_url: str) -> list[TestResult]:
        """Test Scholar API endpoints."""
        return [
            self._run_test(
                "Info endpoint",
                f"{base_url}/api/v1/scholar/info/",
                expected_status=200,
            ),
            self._run_test(
                "Search without query (400)",
                f"{base_url}/api/v1/scholar/search/",
                expected_status=400,
            ),
            self._run_test(
                "Search with query",
                f"{base_url}/api/v1/scholar/search/?q=test&limit=1",
                expected_status=200,
            ),
            self._run_test(
                "Search BibTeX format",
                f"{base_url}/api/v1/scholar/search/?q=test&format=bibtex&limit=1",
                expected_status=200,
            ),
        ]

    def _test_stats_api(self, base_url: str) -> list[TestResult]:
        """Test Stats API endpoints."""
        return [
            self._run_test(
                "Stats plot (GET)",
                f"{base_url}/api/stats/plot/?test_name=ttest_ind"
                "&data=1,2,3,4,5&data2=2,3,4,5,6",
                expected_status=200,
                preview_url="/api/stats/plot/?test_name=ttest_ind"
                "&data=1,2,3,4,5&data2=2,3,4,5,6",
            ),
            self._run_test(
                "Stats calculate (POST)",
                f"{base_url}/api/stats/calculate/",
                method="POST",
                json_data={
                    "test_name": "ttest_ind",
                    "data": [1, 2, 3, 4, 5],
                    "data2": [2, 3, 4, 5, 6],
                },
                expected_status=200,
            ),
            self._run_test(
                "Stats describe (POST)",
                f"{base_url}/api/stats/describe/",
                method="POST",
                json_data={"data": [1, 2, 3, 4, 5]},
                expected_status=200,
            ),
            self._run_test(
                "Stats recommend (POST)",
                f"{base_url}/api/stats/recommend/",
                method="POST",
                json_data={"n_groups": 2},
                expected_status=200,
            ),
            self._run_test(
                "Stats effect size (POST)",
                f"{base_url}/api/stats/effect-size/",
                method="POST",
                json_data={
                    "measure": "cohens_d",
                    "group1": [1, 2, 3, 4, 5],
                    "group2": [3, 4, 5, 6, 7],
                },
                expected_status=200,
            ),
            self._run_test(
                "Stats power (POST)",
                f"{base_url}/api/stats/power/",
                method="POST",
                json_data={"effect_size": 0.5},
                expected_status=200,
            ),
            self._run_test(
                "Stats correct (POST)",
                f"{base_url}/api/stats/correct/",
                method="POST",
                json_data={
                    "method": "bonferroni",
                    "pvalues": [0.01, 0.04, 0.03],
                },
                expected_status=200,
            ),
            self._run_test(
                "Stats flowchart (GET)",
                f"{base_url}/api/stats/flowchart/",
                expected_status=200,
            ),
        ]

    def _test_plot_api(self, base_url: str) -> list[TestResult]:
        """Test Plot API endpoints."""
        plot_tests = [
            ("Plot line (GET)", "kind=line&x=1,2,3,4,5&y=1,4,9,16,25"),
            ("Plot scatter (GET)", "kind=scatter&x=1,2,3&y=5,3,4"),
            ("Plot bar (GET)", "kind=bar&x=A,B,C&y=10,20,30"),
            ("Plot histogram (GET)", "kind=hist&data=1,2,2,3,3,3,4,4,5"),
            (
                "Plot violin (GET)",
                "kind=violin&data=1,2,3,4,5&data2=3,4,5,6,7",
            ),
            ("Plot pie (GET)", "kind=pie&data=30,50,20&labels=A,B,C"),
            (
                "Plot heatmap (GET)",
                "kind=heatmap&data=1,2,3,4,5,6,7,8,9&nrows=3&ncols=3",
            ),
            (
                "Plot errorbar (GET)",
                "kind=errorbar&x=1,2,3&y=10,20,15&yerr=2,3,1",
            ),
        ]

        results = []
        for name, qs in plot_tests:
            results.append(
                self._run_test(
                    name,
                    f"{base_url}/api/plot/?{qs}",
                    expected_status=200,
                    preview_url=f"/api/plot/?{qs}",
                )
            )

        # POST test
        results.append(
            self._run_test(
                "Plot POST (JSON spec)",
                f"{base_url}/api/plot/",
                method="POST",
                json_data={
                    "figure": {"width_mm": 80, "height_mm": 60},
                    "plots": [
                        {"type": "line", "x": [1, 2, 3], "y": [1, 4, 9]},
                    ],
                },
                expected_status=200,
            )
        )
        # Error cases
        results.append(
            self._run_test(
                "Plot missing kind (400)",
                f"{base_url}/api/plot/",
                expected_status=400,
            )
        )
        results.append(
            self._run_test(
                "Plot invalid kind (400)",
                f"{base_url}/api/plot/?kind=invalid",
                expected_status=400,
            )
        )
        return results

    def _test_auth_api(self, base_url: str) -> list[TestResult]:
        """Test Auth API endpoints."""
        return [
            self._run_test(
                "Token rejects empty",
                f"{base_url}/api/token/",
                method="POST",
                json_data={},
                expected_status=400,
            ),
            self._run_test(
                "Token rejects invalid",
                f"{base_url}/api/token/",
                method="POST",
                json_data={"username": "invalid_xyz", "password": "wrong"},
                expected_status=401,
            ),
        ]

    def _test_web_api_docs(self, base_url: str) -> list[TestResult]:
        """Test Web API documentation pages."""
        from apps.infra.public_app.config.api_docs import (
            API_DOC_SECTION_ORDER,
            API_DOC_SECTIONS,
        )

        results = [
            self._run_test(
                "Docs index",
                f"{base_url}/docs/web-api/",
                expected_status=200,
                preview_url="/docs/web-api/",
            ),
        ]
        for key in API_DOC_SECTION_ORDER:
            section = API_DOC_SECTIONS[key]
            results.append(
                self._run_test(
                    section["text"],
                    f"{base_url}/docs/web-api/{key}/",
                    expected_status=200,
                    preview_url=f"/docs/web-api/{key}/",
                )
            )
        # Legacy redirect
        results.append(
            self._run_test(
                "Legacy redirect (/api-docs/)",
                f"{base_url}/api-docs/",
                expected_status=302,
            )
        )
        return results


def run_tests_api(request, category):
    """API endpoint: run tests for a single category, return JSON.

    Requires staff authentication to prevent external crawlers from
    triggering resource-intensive tests.
    """
    # Block unauthenticated/non-staff access (prevents crawler-induced DoS)
    if not request.user.is_authenticated or not request.user.is_staff:
        return JsonResponse(
            {"error": "Staff authentication required"},
            status=403,
        )

    method_name = _CATEGORY_METHOD_MAP.get(category)
    if not method_name:
        return JsonResponse({"error": f"Unknown category: {category}"}, status=404)

    base_url = "http://localhost:8000"
    runner = TestMonitorView()
    runner.request = request

    results = getattr(runner, method_name)(base_url)

    return JsonResponse(
        {
            "category": category,
            "results": [
                {
                    "name": r.name,
                    "endpoint": r.endpoint,
                    "method": r.method,
                    "expected_status": r.expected_status,
                    "actual_status": r.actual_status,
                    "passed": r.passed,
                    "duration_ms": r.duration_ms,
                    "error": r.error,
                    "preview_url": r.preview_url,
                }
                for r in results
            ],
            "passed_count": sum(1 for r in results if r.passed),
            "total": len(results),
            "all_passed": all(r.passed for r in results),
        }
    )
