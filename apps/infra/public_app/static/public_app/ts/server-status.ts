/**
 * Server Status - Main Entry Point
 *
 * Charts are drawn IN THE BROWSER as inline SVG from a single JSON read
 * (/api/server-metrics/series/). The previous implementation asked the
 * backend for eight pre-rendered matplotlib PNGs, which a Celery beat task
 * regenerated 48 times a minute (8 metrics x 3 windows x 2 themes) — about
 * 69,120 renders a day. That fan-out put the `celery` queue ~97,000 messages
 * deep on prod. Operator decision, 2026-07-30: lightweight, web-native charts
 * instead.
 *
 * This module handles:
 * - Time span selection (1h, 6h, 24h)
 * - Theme changes (re-draw from the payload in memory; no refetch)
 * - Real-time metric value updates
 * - Polling shutdown after repeated errors
 */

import { ChartPanels } from "./_server-status/chart-panels";
import { updateMetrics } from "./_server-status/metrics-updater";

// State
let currentTimeSpanMinutes = 60;
let panels: ChartPanels | null = null;

// Track intervals for cleanup after repeated errors
let chartIntervalId: number | null = null;
let metricsIntervalId: number | null = null;
let consecutiveErrors = 0;
const MAX_CONSECUTIVE_ERRORS = 5;

// The series payload only changes when collect_server_metrics writes a new
// row (every 60s in prod), so polling faster would just re-download the same
// numbers.
const CHART_REFRESH_MS = 60000;
const METRICS_REFRESH_MS = 2000;

/**
 * Stop all polling intervals after too many errors.
 */
function stopAllPolling(reason: string): void {
  console.log(`[server-status] Stopping all polling: ${reason}`);

  if (chartIntervalId) {
    clearInterval(chartIntervalId);
    chartIntervalId = null;
  }
  if (metricsIntervalId) {
    clearInterval(metricsIntervalId);
    metricsIntervalId = null;
  }
}

// Expose stop function globally for other modules
(window as unknown as Record<string, unknown>).stopServerStatusPolling =
  stopAllPolling;

/**
 * Reload the chart data for the currently selected time span.
 */
function reloadCharts(): void {
  if (!panels) return;
  void panels.load(currentTimeSpanMinutes);
}

/**
 * Setup time span selector buttons
 */
function setupTimeSpanSelector(): void {
  const selector = document.getElementById("timeSpanSelector");
  if (!selector) return;

  selector.addEventListener("click", (e) => {
    const target = e.target as HTMLElement;
    if (!target.classList.contains("time-span-btn")) return;

    const minutes = parseInt(target.dataset.minutes || "60", 10);
    if (minutes === currentTimeSpanMinutes) return;

    // Update button states
    selector.querySelectorAll(".time-span-btn").forEach((btn) => {
      btn.classList.remove("active");
    });
    target.classList.add("active");

    currentTimeSpanMinutes = minutes;
    reloadCharts();
  });
}

/**
 * Setup theme change listener.
 *
 * Colours live in CSS custom properties that the SVG renderer reads at draw
 * time, so a theme flip is a pure re-draw of data already in memory — no
 * network round trip, and no second server-side render per theme.
 */
function setupThemeListener(): void {
  const observer = new MutationObserver((mutations) => {
    for (const mutation of mutations) {
      if (mutation.attributeName === "data-theme") {
        panels?.redraw();
        break;
      }
    }
  });

  observer.observe(document.documentElement, {
    attributes: true,
    attributeFilter: ["data-theme"],
  });
}

/**
 * Wrapper for updateMetrics that tracks errors and stops polling if too many failures
 */
async function safeUpdateMetrics(): Promise<void> {
  try {
    await updateMetrics();
    consecutiveErrors = 0; // Reset on success
  } catch {
    consecutiveErrors++;
    console.warn(
      `[server-status] Metrics error (${consecutiveErrors}/${MAX_CONSECUTIVE_ERRORS})`,
    );
    if (consecutiveErrors >= MAX_CONSECUTIVE_ERRORS) {
      stopAllPolling("Too many consecutive errors");
    }
  }
}

/**
 * Initialize server status page
 */
function initializeServerStatus(): void {
  panels = new ChartPanels();
  if (panels.panelCount === 0) {
    console.error(
      "[server-status] No .svg-chart[data-metric] containers found — " +
        "the metric panels will stay empty.",
    );
  }

  setupTimeSpanSelector();
  setupThemeListener();

  reloadCharts();
  chartIntervalId = window.setInterval(reloadCharts, CHART_REFRESH_MS);

  // Update metric values every 2 seconds
  safeUpdateMetrics();
  metricsIntervalId = window.setInterval(safeUpdateMetrics, METRICS_REFRESH_MS);

  console.log(
    "[server-status] Initialized - SVG charts refresh every 60s, metrics every 2s",
  );
}

// Initialize on page load
window.addEventListener("load", function () {
  initializeServerStatus();
});
