#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test monitoring dashboard view.

Displays API health check results in real-time.
Available in all environments for transparency.
"""

import time
from dataclasses import dataclass, field

import requests
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


class TestMonitorView(TemplateView):
    """Test monitoring dashboard."""

    template_name = "dev_app/tests.html"

    def dispatch(self, request, *args, **kwargs):
        """Allow in all environments for transparency."""
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Use internal URL for self-testing (container listens on 8000,
        # but host-mapped port differs per environment)
        base_url = "http://localhost:8000"
        current_category = self.kwargs.get("category")

        # Build all categories
        categories = [
            TestCategory(
                key="core",
                name="Core Services",
                icon="fas fa-server",
                results=self._test_core_services(base_url),
            ),
            TestCategory(
                key="pages",
                name="Pages",
                icon="fas fa-file",
                results=self._test_pages(base_url),
            ),
            TestCategory(
                key="modules",
                name="Modules",
                icon="fas fa-cubes",
                results=self._test_modules(base_url),
            ),
            TestCategory(
                key="scholar-api",
                name="Scholar API",
                icon="fas fa-book",
                results=self._test_scholar_api(base_url),
            ),
            TestCategory(
                key="stats-api",
                name="Stats API",
                icon="fas fa-chart-bar",
                results=self._test_stats_api(base_url),
            ),
            TestCategory(
                key="plot-api",
                name="Plot API",
                icon="fas fa-palette",
                results=self._test_plot_api(base_url),
            ),
            TestCategory(
                key="auth-api",
                name="Auth API",
                icon="fas fa-key",
                results=self._test_auth_api(base_url),
            ),
        ]

        # Recalculate stats for each category
        for cat in categories:
            cat.calculate_stats()

        # Filter display categories
        if current_category:
            display_categories = [c for c in categories if c.key == current_category]
        else:
            display_categories = categories

        # Calculate totals
        all_results = []
        for cat in categories:
            all_results.extend(cat.results)

        passed = sum(1 for r in all_results if r.passed)
        failed = sum(1 for r in all_results if not r.passed)

        context.update(
            {
                "categories": categories,
                "display_categories": display_categories,
                "current_category": current_category,
                "passed": passed,
                "failed": failed,
                "total": len(all_results),
                "all_passed": failed == 0,
                "base_url": base_url,
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
        # Use shorter timeout to avoid blocking page load
        timeout = 5
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
                endpoint=url.split(self.request.get_host())[-1],
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
                endpoint=url,
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
            self._run_test(
                "API docs page",
                f"{base_url}/api-docs/",
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
