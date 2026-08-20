#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Server-status charts: the Celery render fan-out is gone, the page still draws.

Operator decision (2026-07-30): the /server-status/ figures were being
force-generated with figrecipe/matplotlib on the server.
``generate_status_charts`` fanned out 48 child tasks EVERY 60 SECONDS (8
metrics x 3 time ranges x 2 themes) = ~69,120 matplotlib renders/day, each one
importing matplotlib + numpy + scipy.signal and calling ``configure_mpl``
before a ``savefig(dpi=150)``.

Two facts measured on prod that make the deletion unambiguous:

- IT NEVER DELIVERED A CHART. The output directory ``/app/data/charts`` was
  never a shared volume — ``docker inspect`` shows neither django nor
  celery_worker mounting anything there — so the worker wrote PNGs into its own
  container filesystem while django read a different one.
  ``/api/server-metrics/chart/cpu/?minutes=60`` answered HTTP 503 the whole
  time, while /server-status/ returned HTTP 200 with broken images inside it.
- MOST RENDERS NEVER RAN. The group was dispatched with ``expires=55`` against
  a queue ~55 MINUTES deep, so children were discarded as revoked before a
  worker reached them — and the dispatcher logged "Dispatched 48" and reported
  success every single time.

Contract under test here:

1. The fan-out is GONE — no beat entry in the active schedule OR in either
   settings source file, and the task/render modules are unimportable.
2. ``collect_server_metrics`` is STILL THERE. That is the POSITIVE CONTROL that
   keeps every "is absent" assertion non-vacuous: an empty, renamed, or
   unimported ``CELERY_BEAT_SCHEDULE`` would satisfy the absence assertions for
   free. That failure mode is not hypothetical — the pre-fix run of this very
   file passed one absence assertion vacuously (see ``code_lines_naming``).
3. /server-status/ still renders its charts — the per-metric CONTAINER, its
   JSON DATA SOURCE, and a visible placeholder are all present in the HTML, and
   the PNG ``<img>`` markup is gone. Asserting only HTTP 200 is not enough: a
   200 with a visually empty body is precisely the bug that shipped on
   2026-07-30 (13 launcher tiles in the DOM at 0x0, hidden by CSS).

The endpoint's own behaviour is covered in test_server_metrics_series_api.py.

Real Django test DB via django.test.TestCase — no mocks.
AAA markers (STX-TQ002) on every test.
"""

from __future__ import annotations

import pytest
from django.conf import settings
from django.test import TestCase

from ._status_chart_helpers import (
    CHART_METRICS,
    SERIES_URL,
    SETTINGS_CELERY_PATH,
    SETTINGS_DEV_PATH,
    STATUS_URL,
    code_lines_naming,
    import_error_of,
    seed_metrics,
)

# Names that must not appear in EXECUTABLE settings code.
FORBIDDEN_CHART_NAMES = ("generate-status-charts", "generate_status_charts")


class TestChartFanOutIsGone(TestCase):
    """The 48-task/60s render fan-out must not exist anywhere."""

    def test_beat_schedule_has_no_generate_status_charts(self):
        # Arrange
        schedule = settings.CELERY_BEAT_SCHEDULE
        # Act
        entry_names = set(schedule)
        # Assert
        assert "generate-status-charts" not in entry_names

    def test_beat_schedule_still_has_collect_server_metrics(self):
        # Arrange — POSITIVE CONTROL on the SAME dict: proves the absence
        # assertion above is reading a populated schedule, not an empty one.
        schedule = settings.CELERY_BEAT_SCHEDULE
        # Act
        entry_names = set(schedule)
        # Assert
        assert "collect-server-metrics" in entry_names

    def test_settings_celery_source_declares_no_chart_entry(self):
        # Arrange — this file is the SSoT. The prod PeriodicTask row was
        # disabled by hand (enabled=False) on 2026-07-30; removing the entry
        # HERE is what stops a future deploy from reseeding and re-enabling it.
        source = SETTINGS_CELERY_PATH.read_text()
        # Act
        hits = code_lines_naming(source, FORBIDDEN_CHART_NAMES)
        # Assert
        assert hits == []

    def test_settings_dev_source_declares_no_chart_entry(self):
        # Arrange — settings_dev.py re-declared the entry as a SUBSCRIPT
        # assignment, so removing it from settings_celery.py alone would have
        # left dev still fanning out 48 tasks a minute.
        source = SETTINGS_DEV_PATH.read_text()
        # Act
        hits = code_lines_naming(source, FORBIDDEN_CHART_NAMES)
        # Assert
        assert hits == []

    def test_scanner_finds_a_beat_entry_in_settings_dev(self):
        # Arrange — POSITIVE CONTROL using the SAME scanner on the SAME file:
        # collect-server-metrics is declared in settings_dev.py in exactly the
        # subscript form the chart entry used, so a hit here proves the scanner
        # can see that form at all. Without this pairing, the two absence
        # assertions above are indistinguishable from a scanner matching nothing
        # — which is how the first version of this test passed pre-fix.
        source = SETTINGS_DEV_PATH.read_text()
        # Act
        hits = code_lines_naming(source, ("collect-server-metrics",))
        # Assert
        assert hits != []

    def test_chart_task_is_no_longer_exported(self):
        # Arrange
        from apps.infra.public_app import tasks

        # Act
        exported = set(tasks.__all__)
        # Assert
        assert "generate_status_charts" not in exported

    def test_collect_server_metrics_is_still_exported(self):
        # Arrange — POSITIVE CONTROL: the tasks package imports fine and its
        # __all__ is populated, so the absence check above is not vacuous.
        from apps.infra.public_app import tasks

        # Act
        exported = set(tasks.__all__)
        # Assert
        assert "collect_server_metrics" in exported

    def test_chart_task_module_is_deleted(self):
        # Arrange
        module_name = "apps.infra.public_app.tasks.charts"
        # Act
        raised = import_error_of(module_name)
        # Assert
        assert raised is not None

    def test_metrics_task_module_still_imports(self):
        # Arrange — POSITIVE CONTROL for the import probe: proves
        # ``import_error_of`` returns None for a module that DOES exist, so the
        # deletion assertions are not passing on a broken helper.
        module_name = "apps.infra.public_app.tasks.metrics"
        # Act
        raised = import_error_of(module_name)
        # Assert
        assert raised is None

    def test_matplotlib_chart_generator_is_deleted(self):
        # Arrange
        module_name = "apps.infra.public_app.views.status.chart_generator"
        # Act
        raised = import_error_of(module_name)
        # Assert
        assert raised is not None

    def test_png_chart_view_is_deleted(self):
        # Arrange
        module_name = "apps.infra.public_app.views.status.charts"
        # Act
        raised = import_error_of(module_name)
        # Assert
        assert raised is not None

    def test_scitex_session_chart_renderer_is_deleted(self):
        # Arrange — the @stx.session/SCITEX_STYLE renderer the operator called
        # out by name ("figrecipe を無理に使っていた").
        module_name = "apps.infra.public_app.views.status.chart_renderer"
        # Act
        raised = import_error_of(module_name)
        # Assert
        assert raised is not None


class TestStatusPageRendersChartContainers(TestCase):
    """The page must ship a chart container AND its data source, per metric."""

    @classmethod
    def setUpTestData(cls):
        seed_metrics(minutes=90, step_seconds=60)

    def test_page_returns_ok(self):
        # Arrange
        # Act
        response = self.client.get(STATUS_URL)
        # Assert
        assert response.status_code == 200

    def test_page_declares_the_json_series_endpoint(self):
        # Arrange — the DATA SOURCE. A container with no source renders blank,
        # and chart-panels.ts refuses to guess a default, so this attribute is
        # load-bearing rather than decorative.
        # Act
        response = self.client.get(STATUS_URL)
        # Assert
        assert f'data-series-endpoint="{SERIES_URL}"'.encode() in response.content

    def test_page_renders_a_chart_container_for_every_metric(self):
        # Arrange
        expected = {f'data-metric="{m}"'.encode() for m in CHART_METRICS}
        # Act
        response = self.client.get(STATUS_URL)
        # Assert
        assert {m for m in expected if m in response.content} == expected

    def test_chart_containers_carry_the_svg_chart_class(self):
        # Arrange — the class chart-panels.ts selects on. Without it the
        # containers exist and stay forever empty.
        # Act
        response = self.client.get(STATUS_URL)
        # Assert
        assert response.content.count(b'class="metric-chart svg-chart"') == len(
            CHART_METRICS
        )

    def test_page_no_longer_serves_png_chart_images(self):
        # Arrange — paired with the positive assertions above so this cannot
        # pass merely because the page rendered nothing at all.
        # Act
        response = self.client.get(STATUS_URL)
        # Assert
        assert b"matplotlib-chart" not in response.content

    def test_page_no_longer_links_the_png_chart_endpoint(self):
        # Arrange — the route that answered 503 for its entire life.
        # Act
        response = self.client.get(STATUS_URL)
        # Assert
        assert b"/api/server-metrics/chart/" not in response.content

    def test_every_container_holds_a_visible_placeholder(self):
        # Arrange — an empty <div> is the "200 with a blank body" trap; each
        # container must carry visible text before JS runs.
        # Act
        response = self.client.get(STATUS_URL)
        # Assert
        assert response.content.count(b'class="chart-placeholder"') == len(
            CHART_METRICS
        )

    def test_page_loads_the_chart_theme_stylesheet(self):
        # Arrange — the SVG renderer reads its colours from CSS custom
        # properties defined in charts.css. If that stylesheet is not linked,
        # every stroke falls back to a hardcoded default and the theme-aware
        # design silently degrades. Linked explicitly rather than via an
        # @import chain because two divergent copies of the server-status CSS
        # index exist in this repo (static/ and the app dir).
        # Act
        response = self.client.get(STATUS_URL)
        # Assert
        assert b"public_app/css/server-status/charts.css" in response.content


if __name__ == "__main__":
    import os

    pytest.main([os.path.abspath(__file__)])

# EOF
