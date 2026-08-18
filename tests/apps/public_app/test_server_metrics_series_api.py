#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""/api/server-metrics/series/ — the JSON that replaced 48 PNG renders a minute.

This endpoint is the data source for the browser-drawn /server-status/ charts
(operator decision 2026-07-30). It replaces a Celery beat task that
pre-rendered 8 metrics x 3 time ranges x 2 themes as matplotlib PNGs every 60
seconds — ~69,120 renders/day that were never reachable, because the output
directory was not a shared volume between the worker and django.

What is pinned here, and why each one is a correctness property rather than a
nice-to-have:

- DOWNSAMPLING is a bucket MEAN, capped at ``max_points``. The deleted code used
  ``scipy.signal.resample``, which is FFT-based: it assumes the signal is
  periodic, so on a non-periodic load trace it rings (Gibbs) and can emit
  NEGATIVE values for a metric that is non-negative by construction. A bucket
  mean cannot produce a value outside the observed range.
- I/O RATES come from deltas of cumulative counters and are clamped at 0, so a
  counter reset shows a gap or a zero, never negative throughput.
- COLOUR is a CSS custom property NAME, never a resolved value. That is what
  makes the old per-theme render (half the 48) unnecessary.
- FRESHNESS is reported. Prod on 2026-07-30 had rows 2.4 HOURS old, which means
  a 24h window still returns real data that a chart would draw as if it were
  live. "Stale" and "fresh" must be distinguishable in the payload.
- AN EMPTY WINDOW IS A 503, not a zero-filled series. A flat zero line on a
  load chart is a believable "idle host" and is indistinguishable from the
  truth. No silent fallback.

Real Django test DB via django.test.TestCase — no mocks.
AAA markers (STX-TQ002) on every test.
"""

from __future__ import annotations

import json

import pytest
from django.test import TestCase

from ._status_chart_helpers import CHART_METRICS, SERIES_URL, seed_metrics


class TestSeriesEndpointServesData(TestCase):
    """One JSON read feeds all eight panels."""

    @classmethod
    def setUpTestData(cls):
        seed_metrics(minutes=90, step_seconds=60)

    def _payload(self, minutes: int = 60) -> dict:
        return json.loads(self.client.get(SERIES_URL, {"minutes": minutes}).content)

    def test_endpoint_returns_ok(self):
        # Arrange
        # Act
        response = self.client.get(SERIES_URL, {"minutes": 60})
        # Assert
        assert response.status_code == 200

    def test_payload_carries_every_chart(self):
        # Arrange
        # Act
        payload = self._payload()
        # Assert
        assert set(payload["charts"]) == set(CHART_METRICS)

    def test_timestamps_and_values_are_the_same_length(self):
        # Arrange — a renderer indexes values by timestamp position; a mismatch
        # silently truncates or shifts the whole trace in time.
        payload = self._payload()
        # Act
        cpu_values = payload["charts"]["cpu"]["series"][0]["values"]
        # Assert
        assert len(cpu_values) == len(payload["t"])

    def test_payload_is_downsampled_to_the_point_budget(self):
        # Arrange — 90 min of rows at 60s is ~90 samples; a 24h request must
        # still be capped so the payload stays in the low tens of kB.
        # Act
        payload = self._payload(1440)
        # Assert
        assert len(payload["t"]) <= payload["max_points"]

    def test_cpu_series_reports_available(self):
        # Arrange
        # Act
        payload = self._payload()
        # Assert
        assert payload["charts"]["cpu"]["available"] is True

    def test_percent_chart_declares_a_fixed_axis_maximum(self):
        # Arrange — a percentage axis must not autoscale, or a 4% idle host
        # looks identical to a 100% pegged one.
        # Act
        payload = self._payload()
        # Assert
        assert payload["charts"]["cpu"]["y_max"] == 100

    def test_io_charts_carry_two_series(self):
        # Arrange
        # Act
        payload = self._payload()
        # Assert
        assert len(payload["charts"]["net_io"]["series"]) == 2

    def test_io_rates_are_never_negative(self):
        # Arrange — rates are deltas of cumulative counters; a reset must clamp
        # to 0. scipy.signal.resample could not guarantee this.
        payload = self._payload()
        # Act
        values = [
            v
            for series in payload["charts"]["disk_io"]["series"]
            for v in series["values"]
            if v is not None
        ]
        # Assert
        assert all(v >= 0 for v in values)

    def test_io_rates_are_actually_computed(self):
        # Arrange — POSITIVE CONTROL for the clamp above: "no negatives" passes
        # for free if every value is None. The seed's counters advance by
        # 100 MB per 60s step, so a real rate must be present.
        payload = self._payload()
        # Act
        values = [
            v
            for series in payload["charts"]["disk_io"]["series"]
            for v in series["values"]
            if v is not None
        ]
        # Assert
        assert any(v > 0 for v in values)

    def test_downsampled_values_stay_inside_the_observed_range(self):
        # Arrange — the seed's cpu_percent is 10..29 by construction. An
        # FFT resample can overshoot this; a bucket mean cannot.
        payload = self._payload()
        # Act
        values = [v for v in payload["charts"]["cpu"]["series"][0]["values"] if v is not None]
        # Assert
        assert min(values) >= 10.0 and max(values) <= 29.0

    def test_each_series_names_a_theme_css_variable(self):
        # Arrange — colour is resolved by the browser against the active theme.
        payload = self._payload()
        # Act
        color_vars = [
            series["color_var"]
            for chart in payload["charts"].values()
            for series in chart["series"]
        ]
        # Assert
        assert all(v.startswith("--chart-") for v in color_vars)

    def test_no_series_ships_a_resolved_colour(self):
        # Arrange — a literal hex here would reintroduce the per-theme problem
        # that forced the backend to render every chart twice.
        payload = self._payload()
        # Act
        serialized = json.dumps(payload["charts"])
        # Assert
        assert "#" not in serialized

    def test_unsupported_time_range_is_rejected(self):
        # Arrange — no silent normalisation onto a neighbouring window, which
        # would show the caller a different time range than it asked for.
        # Act
        response = self.client.get(SERIES_URL, {"minutes": 99})
        # Assert
        assert response.status_code == 400

    def test_non_numeric_time_range_is_rejected(self):
        # Arrange
        # Act
        response = self.client.get(SERIES_URL, {"minutes": "sixty"})
        # Assert
        assert response.status_code == 400

    def test_gpu_without_samples_is_marked_unavailable(self):
        # Arrange — the seed leaves gpu_percent NULL.
        # Act
        payload = self._payload()
        # Assert
        assert payload["charts"]["gpu"]["available"] is False

    def test_unavailable_chart_states_a_reason(self):
        # Arrange — no silent fallback: "no data" must say so.
        # Act
        payload = self._payload()
        # Assert
        assert payload["charts"]["gpu"]["reason"]

    def test_unavailable_chart_is_not_zero_filled(self):
        # Arrange — the whole point: a metric with no samples must not arrive as
        # zeros, which a chart would draw as a convincing flat idle line.
        payload = self._payload()
        # Act
        gpu_values = payload["charts"]["gpu"]["series"][0]["values"]
        # Assert
        assert all(v is None for v in gpu_values)


class TestSeriesEndpointReportsFreshness(TestCase):
    """A window whose newest row is recent must say so."""

    @classmethod
    def setUpTestData(cls):
        seed_metrics(minutes=90, step_seconds=60)

    def test_fresh_window_is_not_stale(self):
        # Arrange
        # Act
        payload = json.loads(self.client.get(SERIES_URL, {"minutes": 60}).content)
        # Assert
        assert payload["stale"] is False

    def test_fresh_window_carries_no_stale_reason(self):
        # Arrange
        # Act
        payload = json.loads(self.client.get(SERIES_URL, {"minutes": 60}).content)
        # Assert
        assert payload["stale_reason"] is None

    def test_fresh_window_reports_a_small_sample_age(self):
        # Arrange
        # Act
        payload = json.loads(self.client.get(SERIES_URL, {"minutes": 60}).content)
        # Assert
        assert payload["latest_sample_age_seconds"] <= payload["stale_after_seconds"]


class TestSeriesEndpointFlagsStaleData(TestCase):
    """Prod's actual 2026-07-30 state: rows exist, but hours old.

    A stale window still holds REAL data so it must be drawn — but it must be
    distinguishable from a fresh one, or the page presents a two-hour-old trace
    as live monitoring. This is the pair to the empty-window 503 below: both
    mean "collect_server_metrics is not running", and neither may be silent.
    """

    @classmethod
    def setUpTestData(cls):
        seed_metrics(minutes=600, step_seconds=300, ends_minutes_ago=144)

    def test_stale_window_is_flagged(self):
        # Arrange
        # Act
        payload = json.loads(self.client.get(SERIES_URL, {"minutes": 1440}).content)
        # Assert
        assert payload["stale"] is True

    def test_stale_window_states_a_reason(self):
        # Arrange
        # Act
        payload = json.loads(self.client.get(SERIES_URL, {"minutes": 1440}).content)
        # Assert
        assert "old" in payload["stale_reason"]

    def test_stale_window_reports_the_sample_age(self):
        # Arrange — 144 min = 8,640s; slack allows for test wall-clock drift.
        # Act
        payload = json.loads(self.client.get(SERIES_URL, {"minutes": 1440}).content)
        # Assert
        assert payload["latest_sample_age_seconds"] >= 8600

    def test_stale_window_still_serves_its_real_data(self):
        # Arrange — POSITIVE CONTROL for the flag: stale must not mean empty, or
        # "stale" and "no data" collapse into one indistinguishable state.
        # Act
        payload = json.loads(self.client.get(SERIES_URL, {"minutes": 1440}).content)
        # Assert
        assert payload["charts"]["cpu"]["available"] is True


class TestSeriesEndpointRefusesWhenEmpty(TestCase):
    """Missing metrics must be loud, not a flat zero line."""

    def test_no_rows_returns_service_unavailable(self):
        # Arrange — empty ServerMetrics table (no setUpTestData here).
        # Act
        response = self.client.get(SERIES_URL, {"minutes": 60})
        # Assert
        assert response.status_code == 503

    def test_no_rows_names_the_error(self):
        # Arrange
        # Act
        payload = json.loads(self.client.get(SERIES_URL, {"minutes": 60}).content)
        # Assert
        assert payload["error"] == "no-metrics"

    def test_no_rows_never_returns_a_charts_payload(self):
        # Arrange — a "charts" key with empty series is exactly what a chart
        # renderer would draw as 0% load across the window.
        # Act
        payload = json.loads(self.client.get(SERIES_URL, {"minutes": 60}).content)
        # Assert
        assert "charts" not in payload

    def test_never_ran_reports_a_null_last_sample(self):
        # Arrange — distinguishes "the collector never ran" from "it stopped N
        # hours ago" (the state prod was in on 2026-07-30).
        # Act
        payload = json.loads(self.client.get(SERIES_URL, {"minutes": 60}).content)
        # Assert
        assert payload["latest_sample_at"] is None


class TestEmptyWindowDistinguishesStoppedFromNeverRan(TestCase):
    """An empty 1h window while older rows exist means "stopped", not "never"."""

    @classmethod
    def setUpTestData(cls):
        seed_metrics(minutes=120, step_seconds=300, ends_minutes_ago=144)

    def test_stopped_collector_reports_the_last_sample_age(self):
        # Arrange — the requested 60min window holds nothing, but the table does.
        # Act
        payload = json.loads(self.client.get(SERIES_URL, {"minutes": 60}).content)
        # Assert
        assert payload["latest_sample_age_seconds"] >= 8600

    def test_stopped_collector_still_returns_503(self):
        # Arrange
        # Act
        response = self.client.get(SERIES_URL, {"minutes": 60})
        # Assert
        assert response.status_code == 503


if __name__ == "__main__":
    import os

    pytest.main([os.path.abspath(__file__)])

# EOF
