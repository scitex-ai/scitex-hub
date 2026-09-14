/**
 * Dock drop rules: an app is in the dock or on the grid, never both, and the
 * dock refuses apps beyond its capacity.
 */

import { describe, expect, it } from "vitest";

import {
  dockCapacity,
  dockInsertIndex,
  dropIntoDock,
  dropOutOfDock,
  dropZoneFor,
} from "@apps_app/_launcher/dock-drop";

const DOCK_BOX = { left: 10, top: 780, right: 380, bottom: 840 };

describe("dropZoneFor", () => {
  it("reads a pointer inside the dock as a dock drop", () => {
    // Arrange
    const point = { x: 200, y: 810 };
    // Act
    const zone = dropZoneFor(point, DOCK_BOX);
    // Assert
    expect(zone).toBe("dock");
  });

  it("still catches a pointer just above the dock edge", () => {
    // Arrange
    const point = { x: 200, y: 772 };
    // Act
    const zone = dropZoneFor(point, DOCK_BOX);
    // Assert
    expect(zone).toBe("dock");
  });

  it("reads a pointer over the grid as a grid drop", () => {
    // Arrange
    const point = { x: 200, y: 400 };
    // Act
    const zone = dropZoneFor(point, DOCK_BOX);
    // Assert
    expect(zone).toBe("grid");
  });

  it("treats a missing dock as the grid", () => {
    // Arrange
    const point = { x: 200, y: 810 };
    // Act
    const zone = dropZoneFor(point, null);
    // Assert
    expect(zone).toBe("grid");
  });
});

describe("dockInsertIndex", () => {
  it("lands between the buttons whose centres the pointer is between", () => {
    // Arrange
    const centers = [60, 120, 180, 240];
    // Act
    const index = dockInsertIndex(150, centers);
    // Assert
    expect(index).toBe(2);
  });

  it("lands at the end when the pointer is past every button", () => {
    // Arrange
    const centers = [60, 120];
    // Act
    const index = dockInsertIndex(300, centers);
    // Assert
    expect(index).toBe(2);
  });
});

describe("dockCapacity", () => {
  it("uses the server limit when the dock is wide enough", () => {
    // Arrange
    const appsWidth = 480;
    // Act
    const capacity = dockCapacity(appsWidth, 5);
    // Assert
    expect(capacity).toBe(5);
  });

  it("holds fewer apps when the dock is too narrow for the server limit", () => {
    // Arrange
    const appsWidth = 170;
    // Act
    const capacity = dockCapacity(appsWidth, 5);
    // Assert
    expect(capacity).toBe(4);
  });

  it("falls back to the server limit before layout", () => {
    // Arrange
    const appsWidth = 0;
    // Act
    const capacity = dockCapacity(appsWidth, 5);
    // Assert
    expect(capacity).toBe(5);
  });
});

describe("dropIntoDock", () => {
  it("inserts a grid app at the drop slot", () => {
    // Arrange
    const dock = ["launcher", "home", "chat"];
    // Act
    const change = dropIntoDock(dock, "scholar", 1, 5);
    // Assert
    expect(change.dock).toEqual(["launcher", "scholar", "home", "chat"]);
  });

  it("refuses a grid app when the dock is full", () => {
    // Arrange
    const dock = ["launcher", "home", "chat", "store", "docs"];
    // Act
    const change = dropIntoDock(dock, "scholar", 2, 5);
    // Assert
    expect(change.refusal).toBe("full");
  });

  it("leaves a full dock unchanged when it refuses", () => {
    // Arrange
    const dock = ["launcher", "home", "chat", "store", "docs"];
    // Act
    const change = dropIntoDock(dock, "scholar", 2, 5);
    // Assert
    expect(change.dock).toBe(dock);
  });

  it("reorders an app already in a full dock", () => {
    // Arrange
    const dock = ["launcher", "home", "chat", "store", "docs"];
    // Act
    const change = dropIntoDock(dock, "docs", 0, 5);
    // Assert
    expect(change.dock).toEqual(["docs", "launcher", "home", "chat", "store"]);
  });

  it("never lists an app twice", () => {
    // Arrange
    const dock = ["launcher", "home", "chat"];
    // Act
    const change = dropIntoDock(dock, "home", 3, 5);
    // Assert
    expect(change.dock.filter((name) => name === "home")).toHaveLength(1);
  });
});

describe("dropOutOfDock", () => {
  it("removes a dragged-out app from the dock", () => {
    // Arrange
    const dock = ["launcher", "home", "chat"];
    // Act
    const change = dropOutOfDock(dock, "chat", ["launcher"]);
    // Assert
    expect(change.dock).toEqual(["launcher", "home"]);
  });

  it("keeps Home in the dock", () => {
    // Arrange
    const dock = ["launcher", "home", "chat"];
    // Act
    const change = dropOutOfDock(dock, "launcher", ["launcher"]);
    // Assert
    expect(change.refusal).toBe("fixed");
  });
});
