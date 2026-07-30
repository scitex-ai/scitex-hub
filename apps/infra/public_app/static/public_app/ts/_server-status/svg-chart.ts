/**
 * Inline-SVG line chart — no chart library, no CDN, no canvas.
 *
 * Built for the /server-status/ metric panels after the operator's
 * 2026-07-30 decision to stop force-rendering them with figrecipe/matplotlib
 * on the server (48 Celery tasks every 60s, ~69k renders/day, which put the
 * `celery` queue ~97k messages deep and starved the visitor-pool cleanup).
 *
 * Theme handling is the reason this is not a PNG: every colour is read from
 * a CSS custom property on the host element, so light/dark follow the page's
 * `data-theme` with no second copy of anything. The old path rendered every
 * chart TWICE — once per theme — purely because a PNG cannot ask what theme
 * it is being displayed in.
 *
 * A missing value stays missing: nulls break the line instead of being
 * drawn as zero, because a fabricated zero on a load chart reads as "idle
 * host" and is indistinguishable from the truth.
 */

import type { ChartPayload, SeriesLine } from "./series-client";

/** Logical drawing surface; the SVG scales to its container. */
const VIEW_W = 500;
const VIEW_H = 300;

const PAD_LEFT = 54;
const PAD_RIGHT = 12;
const PAD_TOP = 28;
const PAD_BOTTOM = 42;

const PLOT_W = VIEW_W - PAD_LEFT - PAD_RIGHT;
const PLOT_H = VIEW_H - PAD_TOP - PAD_BOTTOM;

const Y_TICKS = 4;
const X_TICKS = 4;

const FONT_SIZE = 13;
const AXIS_LABEL_SIZE = 13;

export interface ChartGeometry {
  xOf(index: number): number;
  yOf(value: number): number;
  count: number;
  yMax: number;
}

/** Resolve a CSS custom property against the host's computed style. */
function cssVar(host: HTMLElement, name: string, fallback: string): string {
  const value = getComputedStyle(host).getPropertyValue(name).trim();
  return value || fallback;
}

function escapeText(value: string): string {
  return value
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

/** Round a maximum up to a readable tick boundary. */
function niceMax(raw: number, integer: boolean): number {
  if (!(raw > 0)) return integer ? 1 : 1;
  const magnitude = Math.pow(10, Math.floor(Math.log10(raw)));
  for (const step of [1, 2, 2.5, 5, 10]) {
    const candidate = step * magnitude;
    if (candidate >= raw)
      return integer ? Math.max(1, Math.ceil(candidate)) : candidate;
  }
  return integer ? Math.max(1, Math.ceil(10 * magnitude)) : 10 * magnitude;
}

function observedMax(series: SeriesLine[]): number {
  let max = 0;
  for (const line of series) {
    for (const value of line.values) {
      if (value !== null && value > max) max = value;
    }
  }
  return max;
}

export function formatValue(
  value: number,
  unit: string,
  integer: boolean,
): string {
  if (integer) return `${Math.round(value)}${unit}`;
  if (Math.abs(value) >= 100) return `${value.toFixed(0)}${unit}`;
  if (Math.abs(value) >= 10) return `${value.toFixed(1)}${unit}`;
  return `${value.toFixed(2)}${unit}`;
}

export function formatClock(epochMs: number): string {
  const date = new Date(epochMs);
  const hh = String(date.getHours()).padStart(2, "0");
  const mm = String(date.getMinutes()).padStart(2, "0");
  return `${hh}:${mm}`;
}

function geometry(chart: ChartPayload, count: number): ChartGeometry {
  const yMax =
    chart.y_max !== null && chart.y_max !== undefined
      ? chart.y_max
      : niceMax(observedMax(chart.series), chart.integer);
  const span = count > 1 ? count - 1 : 1;
  return {
    count,
    yMax,
    xOf: (index: number) => PAD_LEFT + (PLOT_W * index) / span,
    yOf: (value: number) =>
      PAD_TOP + PLOT_H - (PLOT_H * Math.min(value, yMax)) / (yMax || 1),
  };
}

/** Contiguous runs of non-null samples; a gap ends a run. */
function segments(values: (number | null)[]): number[][] {
  const runs: number[][] = [];
  let current: number[] = [];
  values.forEach((value, index) => {
    if (value === null) {
      if (current.length) runs.push(current);
      current = [];
    } else {
      current.push(index);
    }
  });
  if (current.length) runs.push(current);
  return runs;
}

function linePath(
  line: SeriesLine,
  geo: ChartGeometry,
  indices: number[],
): string {
  return indices
    .map((index, position) => {
      const command = position === 0 ? "M" : "L";
      const x = geo.xOf(index).toFixed(2);
      const y = geo.yOf(line.values[index] as number).toFixed(2);
      return `${command}${x},${y}`;
    })
    .join(" ");
}

function areaPath(
  line: SeriesLine,
  geo: ChartGeometry,
  indices: number[],
): string {
  const baseline = (PAD_TOP + PLOT_H).toFixed(2);
  const first = geo.xOf(indices[0]).toFixed(2);
  const last = geo.xOf(indices[indices.length - 1]).toFixed(2);
  return `${linePath(line, geo, indices)} L${last},${baseline} L${first},${baseline} Z`;
}

function axes(
  chart: ChartPayload,
  geo: ChartGeometry,
  axis: string,
  text: string,
): string {
  const bottom = PAD_TOP + PLOT_H;
  let svg =
    `<path d="M${PAD_LEFT},${PAD_TOP} L${PAD_LEFT},${bottom} L${PAD_LEFT + PLOT_W},${bottom}" ` +
    `fill="none" stroke="${axis}" stroke-width="1.2" />`;

  for (let tick = 0; tick <= Y_TICKS; tick += 1) {
    const value = (geo.yMax * tick) / Y_TICKS;
    const y = geo.yOf(value);
    svg +=
      `<text x="${PAD_LEFT - 7}" y="${(y + 4).toFixed(2)}" text-anchor="end" ` +
      `font-size="${FONT_SIZE}" fill="${text}">` +
      `${escapeText(formatValue(value, "", chart.integer))}</text>`;
    svg += `<path d="M${PAD_LEFT - 4},${y.toFixed(2)} L${PAD_LEFT},${y.toFixed(2)}" stroke="${axis}" stroke-width="1" />`;
  }

  svg +=
    `<text x="14" y="${(PAD_TOP + PLOT_H / 2).toFixed(2)}" text-anchor="middle" ` +
    `font-size="${AXIS_LABEL_SIZE}" fill="${text}" ` +
    `transform="rotate(-90 14 ${(PAD_TOP + PLOT_H / 2).toFixed(2)})">` +
    `${escapeText(chart.y_label)}</text>`;

  return svg;
}

function xAxisLabels(
  timestamps: number[],
  geo: ChartGeometry,
  axis: string,
  text: string,
): string {
  const bottom = PAD_TOP + PLOT_H;
  let svg = "";
  const ticks = Math.min(X_TICKS, Math.max(1, geo.count - 1));
  for (let tick = 0; tick <= ticks; tick += 1) {
    const index = Math.round(((geo.count - 1) * tick) / ticks);
    const x = geo.xOf(index);
    const anchor = tick === 0 ? "start" : tick === ticks ? "end" : "middle";
    svg += `<path d="M${x.toFixed(2)},${bottom} L${x.toFixed(2)},${bottom + 4}" stroke="${axis}" stroke-width="1" />`;
    svg +=
      `<text x="${x.toFixed(2)}" y="${bottom + 19}" text-anchor="${anchor}" ` +
      `font-size="${FONT_SIZE}" fill="${text}">${escapeText(formatClock(timestamps[index]))}</text>`;
  }
  svg +=
    `<text x="${(PAD_LEFT + PLOT_W / 2).toFixed(2)}" y="${VIEW_H - 4}" text-anchor="middle" ` +
    `font-size="${AXIS_LABEL_SIZE}" fill="${text}">Time</text>`;
  return svg;
}

function legend(chart: ChartPayload, colors: string[], text: string): string {
  if (chart.series.length < 2) return "";
  let svg = "";
  let x = PAD_LEFT + PLOT_W;
  for (let i = chart.series.length - 1; i >= 0; i -= 1) {
    const label = chart.series[i].label;
    const width = label.length * 7 + 22;
    x -= width;
    svg += `<path d="M${x},${PAD_TOP - 12} L${x + 14},${PAD_TOP - 12}" stroke="${colors[i]}" stroke-width="2.5" />`;
    svg +=
      `<text x="${x + 19}" y="${PAD_TOP - 8}" font-size="${FONT_SIZE}" fill="${text}">` +
      `${escapeText(label)}</text>`;
  }
  return svg;
}

/**
 * Short in-chart staleness badge, drawn top-LEFT.
 *
 * Deliberately the compact `stale_badge` and not the full `stale_reason`: the
 * plot box is only PLOT_W user units wide, so a sentence would overflow it and
 * collide with the right-aligned multi-series legend. The full sentence goes in
 * the page-level banner that chart-panels.ts renders above the grid.
 *
 * Colour is --chart-warning, defined per theme in charts.css. It is NOT
 * --status-warning: that global resolves to #b8956a in the light theme, which
 * is 2.78:1 against the warm-white card surface — below the 4.5:1 needed for
 * text this size. --chart-warning is ~5.9:1 light and ~8:1 dark.
 */
function staleBadge(note: string, color: string): string {
  return (
    `<text x="${PAD_LEFT + 2}" y="${PAD_TOP - 9}" font-size="${FONT_SIZE}" ` +
    `font-weight="600" fill="${color}">⚠ ${escapeText(note)}</text>`
  );
}

function message(body: string, text: string): string {
  return (
    `<text x="${(PAD_LEFT + PLOT_W / 2).toFixed(2)}" y="${(PAD_TOP + PLOT_H / 2).toFixed(2)}" ` +
    `text-anchor="middle" font-size="15" fill="${text}">${escapeText(body)}</text>`
  );
}

/**
 * Render one panel into ``host``. Returns the geometry so a caller can wire
 * hover behaviour without recomputing the scales.
 */
export function renderChart(
  host: HTMLElement,
  chart: ChartPayload,
  timestamps: number[],
  staleNote?: string | null,
): ChartGeometry | null {
  const axis = cssVar(host, "--chart-axis", "#b5c7d1");
  const text = cssVar(host, "--chart-text", "#d0dce3");
  const fillOpacity = cssVar(host, "--chart-fill-opacity", "0.16");
  const colors = chart.series.map((line, index) =>
    cssVar(host, line.color_var, index === 0 ? "#36a2eb" : "#ff9f40"),
  );

  const count = timestamps.length;
  const geo = geometry(chart, count);

  let body = axes(chart, geo, axis, text);

  if (!chart.available || count === 0) {
    body += message(chart.reason || "No data for this window", text);
    host.innerHTML = svgShell(chart, body);
    return null;
  }

  body += xAxisLabels(timestamps, geo, axis, text);

  // A stale window still holds real data, so it is drawn — but it is captioned
  // so nobody reads a three-hour-old trace as live monitoring.
  if (staleNote) {
    body += staleBadge(staleNote, cssVar(host, "--chart-warning", "#8a5a12"));
  }

  chart.series.forEach((line, index) => {
    for (const run of segments(line.values)) {
      if (line.fill && run.length > 1) {
        body +=
          `<path d="${areaPath(line, geo, run)}" fill="${colors[index]}" ` +
          `fill-opacity="${fillOpacity}" stroke="none" />`;
      }
      const width = run.length === 1 ? 3 : 1.8;
      const cap = run.length === 1 ? ' stroke-linecap="round"' : "";
      body +=
        `<path d="${linePath(line, geo, run)}" fill="none" stroke="${colors[index]}" ` +
        `stroke-width="${width}" stroke-linejoin="round"${cap} />`;
    }
  });

  body += legend(chart, colors, text);
  host.innerHTML = svgShell(chart, body);
  return geo;
}

function svgShell(chart: ChartPayload, body: string): string {
  return (
    `<svg class="svg-chart-canvas" viewBox="0 0 ${VIEW_W} ${VIEW_H}" ` +
    `preserveAspectRatio="xMidYMid meet" role="img" ` +
    `aria-label="${escapeText(chart.label)}">${body}</svg>`
  );
}

export const PLOT_BOX = {
  left: PAD_LEFT,
  right: PAD_LEFT + PLOT_W,
  top: PAD_TOP,
  bottom: PAD_TOP + PLOT_H,
  viewWidth: VIEW_W,
  viewHeight: VIEW_H,
};
