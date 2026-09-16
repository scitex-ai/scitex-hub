/**
 * Pure view math for the citation graph canvas: world <-> screen, zoom,
 * pinch, fit, tap-to-centre and node sizing. No DOM, so vitest covers it.
 */

import type { Transform } from "./types";

export interface Point {
  x: number;
  y: number;
}

export const MIN_ZOOM = 0.2;
export const MAX_ZOOM = 6;

const clampZoom = (k: number): number =>
  Math.max(MIN_ZOOM, Math.min(MAX_ZOOM, k));

export function worldToScreen(t: Transform, p: Point): Point {
  return { x: p.x * t.k + t.x, y: p.y * t.k + t.y };
}

export function screenToWorld(t: Transform, p: Point): Point {
  return { x: (p.x - t.x) / t.k, y: (p.y - t.y) / t.k };
}

/** Zoom by `factor` keeping the screen point `anchor` fixed. */
export function zoomAt(t: Transform, anchor: Point, factor: number): Transform {
  const k = clampZoom(t.k * factor);
  const w = screenToWorld(t, anchor);
  return { k, x: anchor.x - w.x * k, y: anchor.y - w.y * k };
}

/**
 * Two-finger gesture: the world point under the old midpoint follows the new
 * midpoint, and scale changes by the finger-distance ratio.
 */
export function pinch(
  t: Transform,
  a0: Point,
  b0: Point,
  a1: Point,
  b1: Point,
): Transform {
  const d0 = Math.hypot(b0.x - a0.x, b0.y - a0.y) || 1;
  const d1 = Math.hypot(b1.x - a1.x, b1.y - a1.y) || 1;
  const m0 = { x: (a0.x + b0.x) / 2, y: (a0.y + b0.y) / 2 };
  const m1 = { x: (a1.x + b1.x) / 2, y: (a1.y + b1.y) / 2 };
  const k = clampZoom(t.k * (d1 / d0));
  const w = screenToWorld(t, m0);
  return { k, x: m1.x - w.x * k, y: m1.y - w.y * k };
}

/**
 * Transform that puts world point `p` at the centre of the part of the
 * viewport not covered by a bottom sheet of height `sheetHeight`.
 */
export function centerOn(
  t: Transform,
  p: Point,
  viewWidth: number,
  viewHeight: number,
  sheetHeight = 0,
  zoom?: number,
): Transform {
  const k = clampZoom(zoom ?? t.k);
  const visibleH = Math.max(0, viewHeight - sheetHeight);
  return { k, x: viewWidth / 2 - p.x * k, y: visibleH / 2 - p.y * k };
}

export function fitTransform(
  points: Point[],
  viewWidth: number,
  viewHeight: number,
  padding = 40,
): Transform {
  if (points.length === 0) return { x: viewWidth / 2, y: viewHeight / 2, k: 1 };
  const xs = points.map((p) => p.x);
  const ys = points.map((p) => p.y);
  const minX = Math.min(...xs);
  const maxX = Math.max(...xs);
  const minY = Math.min(...ys);
  const maxY = Math.max(...ys);
  const w = Math.max(maxX - minX, 1);
  const h = Math.max(maxY - minY, 1);
  const k = clampZoom(
    Math.min((viewWidth - padding * 2) / w, (viewHeight - padding * 2) / h, 2),
  );
  const cx = (minX + maxX) / 2;
  const cy = (minY + maxY) / 2;
  return { k, x: viewWidth / 2 - cx * k, y: viewHeight / 2 - cy * k };
}

/** Radius grows with sqrt(citations) so area tracks citation count. */
export function nodeRadius(
  citations: number,
  maxCitations: number,
  isSeed: boolean,
): number {
  const base =
    5 + 17 * Math.sqrt(Math.max(0, citations) / Math.max(1, maxCitations));
  return isSeed ? Math.max(base, 16) : base;
}

/** Linear ease between two transforms, for the tap-to-centre animation. */
export function lerpTransform(
  a: Transform,
  b: Transform,
  s: number,
): Transform {
  const e = s < 0.5 ? 2 * s * s : 1 - Math.pow(-2 * s + 2, 2) / 2;
  return {
    x: a.x + (b.x - a.x) * e,
    y: a.y + (b.y - a.y) * e,
    k: a.k + (b.k - a.k) * e,
  };
}
