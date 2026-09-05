/**
 * When a dragged launcher tile may take another tile's slot.
 *
 * FIELD BUG (operator, real device, 2026-09-05): in edit mode, dragging an icon
 * made the grid "swap left and right ten times a second" — his words:
 * 「1秒の間に10回とか入れ替わってすごく気持ち悪い」. Two causes, both here:
 *
 * 1. THE OLD RULE WAS "TOUCHING", NOT "PASSING". `handleDragMove` reordered as
 *    soon as the pointer was over ANY pixel of a neighbouring tile. One pixel
 *    into the neighbour swapped the two; the dragged tile then occupied that
 *    slot, so the very next pointermove — same finger position, new layout —
 *    met the tile that had just moved into the vacated slot and swapped back.
 *    A pointer resting anywhere near a boundary oscillates at the pointer-event
 *    rate, which is exactly what he saw.
 *
 * 2. HIT-TESTING READ THE ANIMATION, NOT THE LAYOUT. The reorder animates the
 *    displaced tiles over ~200 ms (FLIP), and `document.elementFromPoint` hit-
 *    tests TRANSFORMED boxes, so during that travel it returns tiles at their
 *    in-flight positions. Every frame of the animation could therefore start
 *    another reorder, which restarted the animation, and so on.
 *
 * The iPhone home screen commits a swap only when the dragged icon passes the
 * neighbour's CENTRE, and it does not re-decide while icons are still sliding.
 * :func:`shouldSwap` is that rule, kept pure so it can be tested without a
 * layout engine — jsdom has none, and this is precisely the geometry that broke.
 */

/** The part of a DOMRect this decision needs (so tests need not fake a DOMRect). */
export interface Box {
  left: number;
  top: number;
  width: number;
  height: number;
}

export interface Point {
  x: number;
  y: number;
}

/**
 * Fraction of the target tile that stays "no man's land" around its centre.
 *
 * Without it a pointer parked exactly on the centre line flips on sub-pixel
 * jitter — the same oscillation one order of magnitude smaller. 0.12 is ~9px on
 * the 76px mobile tile: below a fingertip's own tremor, above pixel noise.
 */
export const CENTRE_DEADBAND_RATIO = 0.12;

/**
 * Which axis this pair of tiles is separated along.
 *
 * A launcher grid wraps, so two tiles are either side by side in a row or in
 * different rows. Comparing along the wrong axis is what makes a drag feel
 * random: moving right must not be judged by how far DOWN the pointer is.
 * Rows are considered different when the boxes overlap vertically by less than
 * half a tile.
 */
export function dominantAxis(dragged: Box, target: Box): "x" | "y" {
  const overlap =
    Math.min(dragged.top + dragged.height, target.top + target.height) -
    Math.max(dragged.top, target.top);
  const sameRow = overlap > Math.min(dragged.height, target.height) / 2;
  return sameRow ? "x" : "y";
}

/**
 * Has the pointer passed the target's centre, in the direction of travel?
 *
 * `forward` is DOM order, not screen direction: the dragged tile is moving to a
 * LATER slot. In a left-to-right, top-to-bottom grid that means rightwards
 * along x and downwards along y.
 */
export function crossedCentre(
  pointer: Point,
  target: Box,
  forward: boolean,
  axis: "x" | "y",
): boolean {
  const size = axis === "x" ? target.width : target.height;
  const centre =
    axis === "x"
      ? target.left + target.width / 2
      : target.top + target.height / 2;
  const position = axis === "x" ? pointer.x : pointer.y;
  const deadband = size * CENTRE_DEADBAND_RATIO;
  return forward ? position > centre + deadband : position < centre - deadband;
}

export interface SwapRequest {
  /** Where the finger / cursor is now. */
  pointer: Point;
  /** The tile being dragged, as laid out. */
  dragged: Box;
  /** The tile under the pointer. */
  target: Box;
  /** True when the dragged tile would move to a LATER position in DOM order. */
  forward: boolean;
  /** True while displaced tiles are still travelling to their new slots. */
  travelling: boolean;
}

/**
 * The whole rule: commit a swap only when the pointer has passed the target's
 * centre along the axis that separates the two tiles, and never while the
 * previous swap is still animating.
 */
export function shouldSwap(request: SwapRequest): boolean {
  if (request.travelling) return false;
  const axis = dominantAxis(request.dragged, request.target);
  return crossedCentre(request.pointer, request.target, request.forward, axis);
}
