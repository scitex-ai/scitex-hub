/**
 * site-dock position clamping — the dock (or the minimized grip pill) must
 * never park off-screen.
 *
 * `toPixels` clamps the stored fractions, but the box it measures can be
 * stale: the stylesheets may not have applied yet when the dock restores at
 * DOMContentLoaded, or the minimized state may have changed the box since
 * the fractions were stored. `clampDockToViewport` pins the RESULT against
 * the live box, so a stale measurement parks the dock at an edge instead of
 * off-screen (launcher page #2 with neither dock nor pill, 2026-09-27).
 *
 * Pure geometry, no DOM: nothing here is stubbed.
 */

import { describe, expect, it } from "vitest";

import { clampDockToViewport } from "@/components/_site-dock/position";

const VIEWPORT = { width: 1440, height: 900 };
// Expanded bottom dock at the measured launcher width.
const DOCK = { width: 632, height: 153 };
// Minimized grip pill.
const PILL = { width: 94, height: 44 };

describe("clampDockToViewport", () => {
  it("parks a result computed from a stale narrow box at the right edge", () => {
    // Fractions {x: 1} converted with a 100px-wide pre-stylesheet box land at
    // left = 1440 - 100 - 8 = 1332; the real 632px dock would end at 1964.
    expect(clampDockToViewport(1332, 8, DOCK, VIEWPORT).left).toBe(
      1440 - 632 - 8,
    );
  });

  it("lifts a negative top to the margin", () => {
    expect(clampDockToViewport(800, -40, DOCK, VIEWPORT).top).toBe(8);
  });

  it("leaves an on-screen pill position untouched", () => {
    expect(clampDockToViewport(1338, 8, PILL, VIEWPORT)).toEqual({
      left: 1338,
      top: 8,
    });
  });

  it("anchors a dock larger than the viewport at the margin", () => {
    expect(
      clampDockToViewport(0, 0, { width: 2000, height: 1200 }, VIEWPORT),
    ).toEqual({ left: 8, top: 8 });
  });
});
