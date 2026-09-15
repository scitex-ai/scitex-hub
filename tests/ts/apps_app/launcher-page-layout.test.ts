/**
 * Home pages — how many tiles fit on a page (computePageLayout).
 *
 * Operator, 2026-09-14: the Home grid pages like an iPhone home screen at 390px
 * AND 1440px, with tiles per page fitting the viewport. The numbers below are
 * the real geometry measured on dev (tile ~117px tall at 390, ~112px at 1440;
 * row gap 22px / 26px; 4 / 6 columns), so the tests state what a user sees.
 */

import { describe, expect, it } from "vitest";

import { computePageLayout } from "@apps_app/_launcher/pager";

describe("computePageLayout", () => {
  it("fits a 16-tile grid on one phone page when four rows fit", () => {
    // 390x844: grid top ~67, dock top ~778 -> ~675px for rows after the dots.
    const layout = computePageLayout({
      available: 650,
      tileHeight: 117,
      rowGap: 22,
      cols: 4,
      tileCount: 16,
    });
    expect(layout).toEqual({ rows: 4, perPage: 16, pageCount: 1 });
  });

  it("spills onto a second page when a short phone viewport fits fewer rows", () => {
    // iPhone SE-ish height: only two rows fit, so 16 tiles need two pages.
    const layout = computePageLayout({
      available: 300,
      tileHeight: 117,
      rowGap: 22,
      cols: 4,
      tileCount: 16,
    });
    expect(layout).toEqual({ rows: 2, perPage: 8, pageCount: 2 });
  });

  it("keeps four columns on a desktop, varying only the rows that fit", () => {
    // Operator 2026-09-14: the same app sits at the same grid position on every
    // device, so only the ROW count per page may differ with viewport height.
    const layout = computePageLayout({
      available: 700,
      tileHeight: 130,
      rowGap: 30,
      cols: 4,
      tileCount: 16,
    });
    expect(layout).toEqual({ rows: 4, perPage: 16, pageCount: 1 });
  });

  it("never returns zero rows, even with no room at all", () => {
    const layout = computePageLayout({
      available: 0,
      tileHeight: 117,
      rowGap: 22,
      cols: 4,
      tileCount: 9,
    });
    expect(layout).toEqual({ rows: 1, perPage: 4, pageCount: 3 });
  });

  it("falls back to a sane tile height when the tile is unmeasured", () => {
    // jsdom / pre-layout frames report offsetHeight 0.
    const layout = computePageLayout({
      available: 500,
      tileHeight: 0,
      rowGap: 20,
      cols: 5,
      tileCount: 10,
    });
    expect(layout.rows).toBe(3);
  });

  it("always yields at least one page, even with no tiles", () => {
    const layout = computePageLayout({
      available: 500,
      tileHeight: 117,
      rowGap: 22,
      cols: 4,
      tileCount: 0,
    });
    expect(layout.pageCount).toBe(1);
  });
});
