/**
 * Chart panel orchestration for /server-status/.
 *
 * Owns the eight `.svg-chart[data-metric]` containers: one JSON read feeds
 * them all, and a theme flip re-draws from the payload already in memory
 * instead of asking the server for a second copy in another colour scheme
 * (which is exactly what the deleted 48-task/minute render fan-out did).
 *
 * A failure is rendered as visible text in every panel. Never leave a chart
 * container blank: an empty box reads as "quiet server", and a status page
 * that lies about being fine is worse than one that says it cannot tell.
 */

import type { SeriesResponse } from "./series-client";
import { SERIES_ENDPOINT_ATTR, fetchSeries } from "./series-client";
import { renderChart } from "./svg-chart";
import { attachHover } from "./svg-chart-hover";

export class ChartPanels {
  private readonly hosts: HTMLElement[];
  private readonly endpoint: string | null;
  private payload: SeriesResponse | null = null;

  constructor(root: ParentNode = document) {
    this.hosts = Array.from(
      root.querySelectorAll<HTMLElement>(".svg-chart[data-metric]"),
    );
    const declared = (
      root as ParentNode & { querySelector: typeof document.querySelector }
    )
      .querySelector(`[${SERIES_ENDPOINT_ATTR}]`)
      ?.getAttribute(SERIES_ENDPOINT_ATTR);
    this.endpoint = declared || null;
  }

  get panelCount(): number {
    return this.hosts.length;
  }

  /** Fetch a window and draw it. Returns false when the fetch failed. */
  async load(minutes: number): Promise<boolean> {
    if (!this.endpoint) {
      this.showFailure(
        `The metrics grid is missing its ${SERIES_ENDPOINT_ATTR} attribute, ` +
          "so there is nowhere to read the series from.",
      );
      return false;
    }
    const result = await fetchSeries(this.endpoint, minutes);
    if (!result.ok) {
      this.payload = null;
      this.showFailure(result.failure.detail || result.failure.error);
      return false;
    }
    this.payload = result.data;
    this.draw();
    return true;
  }

  /** Re-draw from the payload already held — used on a theme change. */
  redraw(): void {
    if (this.payload) this.draw();
  }

  /**
   * Show or clear the page-level staleness banner.
   *
   * This is the DEFAULT path on prod today, not an edge case: the celery
   * prefork pool wedges and executes nothing, so `collect_server_metrics` has
   * not written a row in hours and the very first load after deploy lands here.
   * The banner carries the full sentence; each chart also gets a compact badge.
   */
  private setStaleBanner(reason: string | null): void {
    const anchor = this.hosts[0]?.closest(".metrics-grid");
    if (!anchor || !anchor.parentElement) return;

    let banner =
      anchor.parentElement.querySelector<HTMLElement>(".metrics-staleness");
    if (!reason) {
      banner?.remove();
      return;
    }
    if (!banner) {
      banner = document.createElement("div");
      banner.className = "metrics-staleness";
      banner.setAttribute("role", "status");
      anchor.parentElement.insertBefore(banner, anchor);
    }
    banner.textContent = `⚠ ${reason}`;
  }

  private draw(): void {
    const payload = this.payload;
    if (!payload) return;

    this.setStaleBanner(payload.stale ? payload.stale_reason : null);

    for (const host of this.hosts) {
      const metric = host.dataset.metric;
      const chart = metric ? payload.charts[metric] : undefined;
      if (!chart) {
        this.showHostMessage(
          host,
          `No series named "${metric ?? "?"}" in the metrics payload.`,
        );
        continue;
      }
      const geo = renderChart(host, chart, payload.t, payload.stale_badge);
      if (geo) attachHover(host, chart, payload.t, geo);
    }
  }

  private showFailure(detail: string): void {
    for (const host of this.hosts) {
      this.showHostMessage(host, detail);
    }
  }

  private showHostMessage(host: HTMLElement, detail: string): void {
    host.textContent = "";
    const box = document.createElement("div");
    box.className = "chart-placeholder chart-placeholder-error";
    box.textContent = detail;
    host.appendChild(box);
  }
}
