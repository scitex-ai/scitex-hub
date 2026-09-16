/**
 * launcher drag — "icons swap ten times a second" regression.
 *
 * FIELD BUG (operator, real device, 2026-09-05): in the launcher's edit mode,
 * dragging an icon made the grid thrash — 「右に行ったり左に行ったり1秒の間に
 * 10回とか入れ替わってすごく気持ち悪い」 (it goes right, then left, swapping ten
 * times a second; it feels awful). He asked for the iPhone home screen's
 * smoothness.
 *
 * The old rule swapped as soon as the pointer touched ANY pixel of a
 * neighbouring tile, and it re-decided during the 200 ms travel animation,
 * when hit-testing returns tiles at their in-flight positions. Both make the
 * pair swap back on the very next pointermove.
 *
 * These tests run the real decision (`shouldSwap`) against the real geometry of
 * a launcher row — the 76px tiles and 22px gap of the mobile grid — because the
 * geometry IS the bug. jsdom has no layout engine, so the boxes are supplied
 * here exactly as the pager tests supply theirs.
 *
 * WHAT EACH TEST IS FOR
 *   touching_the_edge_does_not_swap        the reported cause: one pixel of
 *                                          overlap used to be enough.
 *   passing_the_centre_swaps               the intended gesture still works.
 *   the_reverse_swap_needs_the_pointer_to_travel_back
 *                                          the oscillation itself: after a
 *                                          swap, the finger standing still
 *                                          must NOT swap the pair back.
 *   travelling_never_swaps                 no decision while tiles slide.
 *   a_tile_in_another_row_is_judged_vertically
 *                                          moving down a row must not be
 *                                          judged by horizontal distance.
 */

import { describe, expect, it } from "vitest";

import {
  crossedCentre,
  dominantAxis,
  shouldSwap,
  type Box,
} from "@apps_app/_launcher/swap-intent";

// The mobile launcher grid: 76px tiles, 22px gap (launcher/grid.css).
const TILE = 76;
const GAP = 22;
const ROW_TOP = 240;
const ROW2_TOP = ROW_TOP + TILE + GAP;

const tileAt = (column: number, top = ROW_TOP): Box => ({
  left: column * (TILE + GAP),
  top,
  width: TILE,
  height: TILE,
});

const DRAGGED = tileAt(0);
const NEIGHBOUR = tileAt(1); // left edge 98, centre 136, right edge 174

describe("launcher swap intent", () => {
  it("does not swap when the pointer has only touched the neighbour's edge", () => {
    // Arrange — one pixel inside the neighbour, the old trigger.
    const pointer = { x: NEIGHBOUR.left + 1, y: ROW_TOP + TILE / 2 };
    // Act
    const swap = shouldSwap({
      pointer,
      dragged: DRAGGED,
      target: NEIGHBOUR,
      forward: true,
      travelling: false,
    });
    // Assert
    expect(swap).toBe(false);
  });

  it("swaps once the pointer has passed the neighbour's centre", () => {
    // Arrange — clearly past the centre line (136) of the neighbour.
    const pointer = { x: NEIGHBOUR.left + TILE * 0.8, y: ROW_TOP + TILE / 2 };
    // Act
    const swap = shouldSwap({
      pointer,
      dragged: DRAGGED,
      target: NEIGHBOUR,
      forward: true,
      travelling: false,
    });
    // Assert
    expect(swap).toBe(true);
  });

  it("does not swap back while the finger stands still after a swap", () => {
    // Arrange — the swap just happened at x=159, so the tiles exchanged slots:
    // the dragged tile now occupies the old neighbour slot and the neighbour
    // sits where the dragged tile was. The finger has not moved, and the swap
    // back would be BACKWARD onto that tile.
    const pointer = { x: NEIGHBOUR.left + TILE * 0.8, y: ROW_TOP + TILE / 2 };
    const neighbourNowFirst = DRAGGED;
    // Act
    const swapsBack = shouldSwap({
      pointer,
      dragged: NEIGHBOUR,
      target: neighbourNowFirst,
      forward: false,
      travelling: false,
    });
    // Assert
    expect(swapsBack).toBe(false);
  });

  it("never swaps while the displaced tiles are still travelling", () => {
    // Arrange — a pointer well past the centre, which would otherwise swap.
    const pointer = { x: NEIGHBOUR.left + TILE * 0.9, y: ROW_TOP + TILE / 2 };
    // Act
    const swap = shouldSwap({
      pointer,
      dragged: DRAGGED,
      target: NEIGHBOUR,
      forward: true,
      travelling: true,
    });
    // Assert
    expect(swap).toBe(false);
  });

  it("judges a tile in another row along the vertical axis", () => {
    // Arrange — same column, next row down.
    const below = tileAt(0, ROW2_TOP);
    // Act
    const axis = dominantAxis(DRAGGED, below);
    // Assert
    expect(axis).toBe("y");
  });

  it("requires the pointer to pass the centre of a tile in the row below", () => {
    // Arrange — inside the tile below, but above its centre line.
    const below = tileAt(0, ROW2_TOP);
    const pointer = { x: TILE / 2, y: below.top + TILE * 0.2 };
    // Act
    const swap = shouldSwap({
      pointer,
      dragged: DRAGGED,
      target: below,
      forward: true,
      travelling: false,
    });
    // Assert
    expect(swap).toBe(false);
  });

  it("keeps a deadband so a pointer resting on the centre line does not flip", () => {
    // Arrange — exactly on the neighbour's centre.
    const pointer = { x: NEIGHBOUR.left + TILE / 2, y: ROW_TOP + TILE / 2 };
    // Act
    const swap = crossedCentre(pointer, NEIGHBOUR, true, "x");
    // Assert
    expect(swap).toBe(false);
  });

  it("treats tiles side by side in a row as a horizontal decision", () => {
    // Arrange — the two tiles of the reported drag.
    const dragged = DRAGGED;
    // Act
    const axis = dominantAxis(dragged, NEIGHBOUR);
    // Assert
    expect(axis).toBe("x");
  });
});
