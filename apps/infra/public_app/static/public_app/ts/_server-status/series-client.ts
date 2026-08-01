/**
 * Series client — fetches the server-status chart data as JSON.
 *
 * Replaces the old path where the browser requested 8 pre-rendered PNGs
 * (each one a matplotlib render the backend produced 48x per minute, for
 * every metric x time range x theme combination). One JSON read now feeds
 * every panel, and the browser draws them.
 *
 * Errors are returned, never swallowed: a caller must be able to tell
 * "the collector is not running" (503) from "you asked for a window we do
 * not offer" (400) and show that on the page instead of a blank chart.
 */

export interface SeriesLine {
  key: string;
  label: string;
  color_var: string;
  fill: boolean;
  values: (number | null)[];
}

export interface ChartPayload {
  label: string;
  y_label: string;
  unit: string;
  y_max: number | null;
  integer: boolean;
  available: boolean;
  reason: string | null;
  series: SeriesLine[];
}

export interface SeriesResponse {
  minutes: number;
  generated_at: string;
  start: string;
  sample_count: number;
  max_points: number;
  /** ISO stamp of the newest row in the window. */
  latest_sample_at: string;
  latest_sample_age_seconds: number;
  stale_after_seconds: number;
  /**
   * True when the newest sample is older than the collector's cadence allows.
   * A stale window still holds REAL data, so it must be drawn — but it must
   * never be presented as live monitoring. Prod sat 2.4h stale on 2026-07-30.
   */
  stale: boolean;
  /** Compact in-chart caption, e.g. "2.4 h stale". */
  stale_badge: string | null;
  /** Full sentence for the page-level banner. */
  stale_reason: string | null;
  t: number[];
  charts: Record<string, ChartPayload>;
}

export interface SeriesFailure {
  error: string;
  detail: string;
}

/**
 * Attribute the page uses to declare where the series come from. The URL is
 * rendered by Django ({% url %}), so the route and the fetch can never drift
 * apart; a missing attribute is an error, not a reason to guess a default.
 */
export const SERIES_ENDPOINT_ATTR = "data-series-endpoint";

export type SeriesResult =
  { ok: true; data: SeriesResponse } | { ok: false; failure: SeriesFailure };

/** Fetch one time window's series. Never throws for an HTTP-level failure. */
export async function fetchSeries(
  endpoint: string,
  minutes: number,
): Promise<SeriesResult> {
  let response: Response;
  try {
    response = await fetch(`${endpoint}?minutes=${minutes}`);
  } catch (error) {
    return {
      ok: false,
      failure: { error: "network", detail: String(error) },
    };
  }

  let body: unknown = null;
  try {
    body = await response.json();
  } catch {
    body = null;
  }

  if (!response.ok) {
    const failure = body as Partial<SeriesFailure> | null;
    return {
      ok: false,
      failure: {
        error: failure?.error ?? `http-${response.status}`,
        detail:
          failure?.detail ?? `Request failed with HTTP ${response.status}.`,
      },
    };
  }

  const data = body as SeriesResponse | null;
  if (!data || !data.charts || !Array.isArray(data.t)) {
    return {
      ok: false,
      failure: {
        error: "malformed",
        detail: "The metrics endpoint returned a payload without any series.",
      },
    };
  }

  return { ok: true, data };
}
