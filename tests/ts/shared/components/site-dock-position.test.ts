/**
 * Site dock position — a bottom drop parks horizontally, never re-centres.
 */

import { describe, expect, it } from "vitest";

import {
  fromPixels,
  SNAP_TO_BOTTOM_PX,
  toPixels,
} from "@/components/_site-dock/position";

const DOCK = { width: 400, height: 120 };
const VIEW = { width: 1280, height: 800 };

describe("dock bottom parking", () => {
  it("a bottom-edge drop keeps the dropped x and pins y to the bottom", () => {
    const top = VIEW.height - DOCK.height - 10; // well inside the snap zone
    const pos = fromPixels(80, top, DOCK, VIEW);
    expect(pos).not.toBeNull();
    expect(pos!.y).toBe(1);
    // x ~= (80 - 8) / (1280 - 400 - 16) — left-ish, not centred.
    expect(pos!.x).toBeLessThan(0.25);
  });

  it("a bottom-right drop stays bottom-right", () => {
    const top = VIEW.height - DOCK.height - SNAP_TO_BOTTOM_PX;
    const pos = fromPixels(800, top, DOCK, VIEW);
    expect(pos).not.toBeNull();
    expect(pos!.y).toBe(1);
    expect(pos!.x).toBeGreaterThan(0.75);
  });

  it("a mid-viewport drop still floats freely", () => {
    const pos = fromPixels(300, 200, DOCK, VIEW);
    expect(pos).not.toBeNull();
    expect(pos!.y).toBeLessThan(1);
  });

  it("a parked bottom position restores to the bottom margin", () => {
    const { top } = toPixels({ x: 0.1, y: 1 }, DOCK, VIEW);
    expect(top).toBe(VIEW.height - DOCK.height - 8);
  });
});
