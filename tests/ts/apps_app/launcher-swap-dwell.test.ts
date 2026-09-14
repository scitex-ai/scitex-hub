/**
 * Swap dwell — icons do not shuffle while a finger merely passes over them.
 *
 * Operator, 2026-09-14 16:34Z: during a drag the other icons jumped as soon as
 * the pointer crossed them. SwapDwell requires the SAME target to stay under
 * the pointer for DWELL_MS (150ms) before a swap is allowed.
 */

import { describe, expect, it } from "vitest";

import { DWELL_MS, SwapDwell } from "@apps_app/_launcher/swap-dwell";

describe("SwapDwell", () => {
  it("does not allow a swap the moment the pointer arrives", () => {
    const dwell = new SwapDwell<string>();
    expect(dwell.update("scholar", 1000)).toBe(DWELL_MS);
  });

  it("allows the swap once the pointer has stayed for 150ms", () => {
    const dwell = new SwapDwell<string>();
    dwell.update("scholar", 1000);
    expect(dwell.update("scholar", 1000 + DWELL_MS)).toBe(0);
  });

  it("restarts the wait when a sweeping finger reaches the next icon", () => {
    const dwell = new SwapDwell<string>();
    dwell.update("scholar", 1000);
    dwell.update("figrecipe", 1100);
    expect(dwell.update("figrecipe", 1200)).toBe(50);
  });

  it("has nothing to swap onto when the pointer is over empty space", () => {
    const dwell = new SwapDwell<string>();
    dwell.update("scholar", 1000);
    expect(dwell.update(null, 1300)).toBeNull();
  });

  it("starts fresh after a swap is made (reset)", () => {
    const dwell = new SwapDwell<string>();
    dwell.update("scholar", 1000);
    dwell.reset();
    expect(dwell.update("scholar", 1400)).toBe(DWELL_MS);
  });
});
