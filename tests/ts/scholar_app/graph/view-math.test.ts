/**
 * Tap-to-centre and gesture math for the citation graph canvas.
 */

import { describe, it, expect } from "vitest";
import {
  centerOn,
  fitTransform,
  nodeRadius,
  pinch,
  screenToWorld,
  worldToScreen,
  zoomAt,
} from "../../../../apps/workspace/scholar_app/static/scholar_app/ts/graph/_view-math";

describe("centerOn", () => {
  it("puts the tapped node at the viewport centre", () => {
    // Arrange
    const t = { x: 13, y: -40, k: 1.5 };
    const node = { x: 120, y: -75 };
    // Act
    const next = centerOn(t, node, 390, 500);
    // Assert
    expect(worldToScreen(next, node)).toEqual({ x: 195, y: 250 });
  });

  it("centres the node in the space left above the bottom sheet", () => {
    // Arrange
    const t = { x: 0, y: 0, k: 2 };
    const node = { x: 10, y: 20 };
    // Act
    const next = centerOn(t, node, 400, 600, 200);
    // Assert
    expect(worldToScreen(next, node)).toEqual({ x: 200, y: 200 });
  });

  it("applies the requested zoom level", () => {
    // Arrange
    const t = { x: 0, y: 0, k: 0.5 };
    // Act
    const next = centerOn(t, { x: 0, y: 0 }, 100, 100, 0, 1);
    // Assert
    expect(next.k).toBe(1);
  });
});

describe("zoomAt", () => {
  it("keeps the world point under the cursor fixed", () => {
    // Arrange
    const t = { x: 30, y: 10, k: 1 };
    const cursor = { x: 200, y: 150 };
    const before = screenToWorld(t, cursor);
    // Act
    const next = zoomAt(t, cursor, 2);
    // Assert
    expect(worldToScreen(next, before)).toEqual(cursor);
  });
});

describe("pinch", () => {
  it("scales by the finger distance ratio", () => {
    // Arrange
    const t = { x: 0, y: 0, k: 1 };
    // Act
    const next = pinch(
      t,
      { x: 100, y: 100 },
      { x: 200, y: 100 },
      { x: 50, y: 100 },
      { x: 250, y: 100 },
    );
    // Assert
    expect(next.k).toBe(2);
  });

  it("keeps the pinched world point under the fingers' midpoint", () => {
    // Arrange
    const t = { x: 5, y: 5, k: 1 };
    const anchor = screenToWorld(t, { x: 150, y: 100 });
    // Act
    const next = pinch(
      t,
      { x: 100, y: 100 },
      { x: 200, y: 100 },
      { x: 120, y: 130 },
      { x: 280, y: 130 },
    );
    // Assert
    const s = worldToScreen(next, anchor);
    expect({
      x: Math.round(s.x * 1e6) / 1e6,
      y: Math.round(s.y * 1e6) / 1e6,
    }).toEqual({ x: 200, y: 130 });
  });
});

describe("fitTransform", () => {
  it("brings every node inside the padded viewport", () => {
    // Arrange
    const pts = [
      { x: -300, y: -50 },
      { x: 500, y: 400 },
    ];
    // Act
    const t = fitTransform(pts, 390, 500, 20);
    // Assert
    const inside = pts
      .map((p) => worldToScreen(t, p))
      .every((s) => s.x >= 19.99 && s.x <= 370.01 && s.y >= 0 && s.y <= 500);
    expect(inside).toBe(true);
  });
});

describe("nodeRadius", () => {
  it("draws more-cited papers larger", () => {
    // Arrange
    const max = 1000;
    // Act
    const small = nodeRadius(10, max, false);
    const large = nodeRadius(900, max, false);
    // Assert
    expect(large).toBeGreaterThan(small);
  });
});
