/**
 * Home grid group bands packed into pages (packGroups).
 *
 * Operator, 2026-09-14: Foundation / Work / System bands, 4 columns at every
 * width, rows never split, and a group that does not fit continues on the next
 * page. Only the rows per page vary with viewport height, never the columns.
 */

import { describe, expect, it } from "vitest";

import { packGroups, type PackMetrics } from "@apps_app/_launcher/group-pack";

const GROUPS = [
  { key: "foundation", label: "Foundation", count: 5 }, // 2 rows
  { key: "work", label: "Work", count: 6 }, // 2 rows
  { key: "system", label: "System", count: 3 }, // 1 row
];

function metrics(available: number): PackMetrics {
  return {
    available,
    cols: 4,
    rowHeight: 110,
    rowGap: 12,
    bandPadding: 20,
    groupGap: 10,
  };
}

describe("packGroups", () => {
  it("fits all three bands on one tall desktop page", () => {
    // 3 bands: 2*110+12+20 = 252, 252, 110+20 = 130; plus 2 gaps = 654.
    const plan = packGroups(GROUPS, metrics(700));
    expect(plan.map((page) => page.map((c) => c.key))).toEqual([
      ["foundation", "work", "system"],
    ]);
  });

  it("moves a band that does not fit to the next page, whole rows only", () => {
    const plan = packGroups(GROUPS, metrics(520));
    expect(
      plan.map((page) => page.map((c) => `${c.key}:${c.start}-${c.end}`)),
    ).toEqual([["foundation:0-5", "work:0-6"], ["system:0-3"]]);
  });

  it("splits a long group across pages at a row boundary", () => {
    const plan = packGroups(
      [{ key: "work", label: "Work", count: 12 }],
      metrics(260),
    );
    expect(plan.map((page) => page.map((c) => [c.start, c.end]))).toEqual([
      [[0, 8]],
      [[8, 12]],
    ]);
  });

  it("puts at least one row on a page even when nothing fits", () => {
    const plan = packGroups(GROUPS, metrics(50));
    expect(plan[0]).toEqual([
      { key: "foundation", label: "Foundation", start: 0, end: 4 },
    ]);
  });

  it("returns one empty page for no groups", () => {
    expect(packGroups([], metrics(500))).toEqual([[]]);
  });
});
