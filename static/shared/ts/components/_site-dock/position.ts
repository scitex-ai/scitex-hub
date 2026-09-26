/**
 * Where a dragged dock sits, stored per device (localStorage).
 *
 * The position is kept as FRACTIONS of the free space (0..1 across, 0..1 down)
 * rather than pixels, so a dock parked in the top-right corner of a portrait
 * phone is still in the top-right corner after a rotation or a window resize,
 * and can never be restored off-screen.
 *
 * "Docked" (no stored position) is the default bottom-centre dock. Dropping the
 * dock back near the bottom edge returns it to that state without changing page
 * geometry; both docked and floating modes are overlays.
 */

export interface DockPosition {
  x: number; // 0 = left edge, 1 = right edge
  y: number; // 0 = top edge, 1 = bottom edge
}

export interface Box {
  width: number;
  height: number;
}

/** Released within this many px of the bottom edge = docked again. */
export const SNAP_TO_BOTTOM_PX = 36;

const clamp01 = (n: number): number => Math.min(1, Math.max(0, n));

export function parsePosition(raw: string | null): DockPosition | null {
  if (!raw) return null;
  try {
    const p = JSON.parse(raw) as DockPosition;
    if (typeof p?.x !== "number" || typeof p?.y !== "number") return null;
    if (!Number.isFinite(p.x) || !Number.isFinite(p.y)) return null;
    return { x: clamp01(p.x), y: clamp01(p.y) };
  } catch {
    return null;
  }
}

/** Pixel left/top for a stored position, inside a viewport with `margin`. */
export function toPixels(
  pos: DockPosition,
  dock: Box,
  viewport: Box,
  margin = 8,
): { left: number; top: number } {
  const freeX = Math.max(0, viewport.width - dock.width - 2 * margin);
  const freeY = Math.max(0, viewport.height - dock.height - 2 * margin);
  return {
    left: Math.round(margin + clamp01(pos.x) * freeX),
    top: Math.round(margin + clamp01(pos.y) * freeY),
  };
}

/**
 * The stored position for a dock dropped with its top-left at (left, top), or
 * null when it was dropped close enough to the bottom to dock again.
 */
export function fromPixels(
  left: number,
  top: number,
  dock: Box,
  viewport: Box,
  margin = 8,
): DockPosition | null {
  const bottomGap = viewport.height - (top + dock.height);
  if (bottomGap <= SNAP_TO_BOTTOM_PX) return null;
  const freeX = Math.max(1, viewport.width - dock.width - 2 * margin);
  const freeY = Math.max(1, viewport.height - dock.height - 2 * margin);
  return {
    x: clamp01((left - margin) / freeX),
    y: clamp01((top - margin) / freeY),
  };
}

/**
 * Pin a computed dock top-left inside the viewport for the dock's CURRENT
 * box. `toPixels` already clamps the stored fractions, but the box it
 * measured can be stale — the stylesheets may not have applied yet when the
 * dock restores at DOMContentLoaded, or the minimized state may have changed
 * the box since the fractions were stored. Clamping the RESULT against the
 * live box keeps at least the margin edge of the dock on-screen, so a stale
 * measurement parks it at an edge instead of off-screen (2026-09-27: dock
 * and grip pill both missing on launcher page #2).
 */
export function clampDockToViewport(
  left: number,
  top: number,
  dock: Box,
  viewport: Box,
  margin = 8,
): { left: number; top: number } {
  const maxLeft = Math.max(margin, viewport.width - dock.width - margin);
  const maxTop = Math.max(margin, viewport.height - dock.height - margin);
  return {
    left: Math.round(Math.min(Math.max(left, margin), maxLeft)),
    top: Math.round(Math.min(Math.max(top, margin), maxTop)),
  };
}
