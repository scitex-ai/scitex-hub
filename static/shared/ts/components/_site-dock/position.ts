/**
 * Where a dragged dock sits, stored per device (localStorage).
 *
 * The position is kept as FRACTIONS of the free space (0..1 across, 0..1 down)
 * rather than pixels, so a dock parked in the top-right corner of a portrait
 * phone is still in the top-right corner after a rotation or a window resize,
 * and can never be restored off-screen.
 *
 * "Docked" (no stored position) is the default bottom-centre dock. Dropping
 * the dock near the bottom edge parks it along the bottom at the dropped
 * horizontal spot — never re-centred. Only an explicit reset (Escape on the
 * grabber) clears the stored position and returns to bottom-centre.
 * Both docked and floating modes are overlays; neither changes page geometry.
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
 * The stored position for a dock dropped with its top-left at (left, top).
 *
 * A drop near the bottom edge parks the dock along the bottom AT THE DROPPED
 * HORIZONTAL SPOT (y pinned to 1) instead of snapping back to bottom-centre:
 * a launcher the user parked bottom-left must stay bottom-left. The centred
 * default is only restored by an explicit reset (Escape on the grabber),
 * which clears the stored position; null is kept as a return inhabitant for
 * that path, not produced here.
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
  const x = clamp01((left - margin) / freeX);
  if (bottomGap <= SNAP_TO_BOTTOM_PX) return { x, y: 1 };
  return { x, y: clamp01((top - margin) / freeY) };
}
