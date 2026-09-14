/**
 * launcher pager geometry — the pure maths behind the Home page dots and the
 * dock's width (operator iPhone report, 2026-09-14).
 *
 * pageIndexFor: which dot is active for a horizontal scroll offset. A swipe on
 * iOS rubber-bands PAST either end before it snaps, so the index must clamp to
 * the pages that exist.
 *
 * dockFrameFor: the dock takes the group panels' left/right edges (the iOS
 * home screen's dock shares the icon grid's side margins), never leaving the
 * viewport.
 */

import { describe, expect, it } from "vitest";

import {
  DOCK_MIN_GUTTER,
  dockFrameFor,
  pageIndexFor,
} from "@apps_app/_launcher/pager";

describe("pageIndexFor", () => {
  it("is the first page at scroll 0", () => {
    // Arrange
    const [scrollLeft, pageWidth, pageCount] = [0, 370, 2];
    // Act
    const index = pageIndexFor(scrollLeft, pageWidth, pageCount);
    // Assert
    expect(index).toBe(0);
  });

  it("is the second page once scrolled one page width", () => {
    // Arrange
    const [scrollLeft, pageWidth, pageCount] = [370, 370, 2];
    // Act
    const index = pageIndexFor(scrollLeft, pageWidth, pageCount);
    // Assert
    expect(index).toBe(1);
  });

  it("rounds a partial swipe past halfway to the next page", () => {
    // Arrange
    const [scrollLeft, pageWidth, pageCount] = [200, 370, 3];
    // Act
    const index = pageIndexFor(scrollLeft, pageWidth, pageCount);
    // Assert
    expect(index).toBe(1);
  });

  it("clamps a rubber-band overscroll past the last page", () => {
    // Arrange
    const [scrollLeft, pageWidth, pageCount] = [900, 370, 2];
    // Act
    const index = pageIndexFor(scrollLeft, pageWidth, pageCount);
    // Assert
    expect(index).toBe(1);
  });

  it("clamps a negative overscroll before the first page", () => {
    // Arrange
    const [scrollLeft, pageWidth, pageCount] = [-240, 370, 2];
    // Act
    const index = pageIndexFor(scrollLeft, pageWidth, pageCount);
    // Assert
    expect(index).toBe(0);
  });

  it("is the first page when the page width is not measured yet", () => {
    // Arrange
    const [scrollLeft, pageWidth, pageCount] = [370, 0, 2];
    // Act
    const index = pageIndexFor(scrollLeft, pageWidth, pageCount);
    // Assert
    expect(index).toBe(0);
  });
});

describe("dockFrameFor", () => {
  it("takes the panels' width on a 390px phone", () => {
    // Arrange
    const [left, right, viewport] = [10, 380, 390];
    // Act
    const frame = dockFrameFor(left, right, viewport);
    // Assert
    expect(frame.width).toBe(370);
  });

  it("centres on the panels, not the viewport, when a sidebar offsets them", () => {
    // Arrange
    const [left, right, viewport] = [399, 1031, 1440];
    // Act
    const frame = dockFrameFor(left, right, viewport);
    // Assert
    expect(frame.center).toBe(715);
  });

  it("never lets the dock run off the left edge", () => {
    // Arrange
    const [left, right, viewport] = [-30, 380, 390];
    // Act
    const frame = dockFrameFor(left, right, viewport);
    // Assert
    expect(frame.center - frame.width / 2).toBe(DOCK_MIN_GUTTER);
  });

  it("never lets the dock run off the right edge", () => {
    // Arrange
    const [left, right, viewport] = [10, 420, 390];
    // Act
    const frame = dockFrameFor(left, right, viewport);
    // Assert
    expect(frame.center + frame.width / 2).toBe(390 - DOCK_MIN_GUTTER);
  });
});
