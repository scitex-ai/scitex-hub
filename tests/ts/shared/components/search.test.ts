/** Keyboard logic of the header command palette (static/shared/ts/components/_search-navigation.ts). */

import { describe, it, expect } from "vitest";

import {
  isOpenPaletteShortcut,
  nextActiveIndex,
  paletteActionForKey,
} from "@/components/_search-navigation";

const plainKey = (key: string) => ({
  key,
  ctrlKey: false,
  metaKey: false,
  altKey: false,
  defaultPrevented: false,
});

describe("nextActiveIndex", () => {
  it("moves down to the next result", () => {
    // Arrange
    const currentIndex = 1;
    // Act
    const index = nextActiveIndex(currentIndex, "next", 5);
    // Assert
    expect(index).toBe(2);
  });

  it("wraps from the last result to the first", () => {
    // Arrange
    const currentIndex = 4;
    // Act
    const index = nextActiveIndex(currentIndex, "next", 5);
    // Assert
    expect(index).toBe(0);
  });

  it("wraps from the first result up to the last", () => {
    // Arrange
    const currentIndex = 0;
    // Act
    const index = nextActiveIndex(currentIndex, "previous", 5);
    // Assert
    expect(index).toBe(4);
  });

  it("jumps to the last result on End", () => {
    // Arrange
    const currentIndex = 1;
    // Act
    const index = nextActiveIndex(currentIndex, "last", 5);
    // Assert
    expect(index).toBe(4);
  });

  it("highlights nothing when there are no results", () => {
    // Arrange
    const currentIndex = 0;
    // Act
    const index = nextActiveIndex(currentIndex, "next", 0);
    // Assert
    expect(index).toBe(-1);
  });
});

describe("paletteActionForKey", () => {
  it("maps Enter to opening the highlighted result", () => {
    // Arrange
    const key = "Enter";
    // Act
    const action = paletteActionForKey(key);
    // Assert
    expect(action).toBe("open");
  });

  it("maps Escape to closing the palette", () => {
    // Arrange
    const key = "Escape";
    // Act
    const action = paletteActionForKey(key);
    // Assert
    expect(action).toBe("close");
  });

  it("ignores ordinary typing", () => {
    // Arrange
    const key = "a";
    // Act
    const action = paletteActionForKey(key);
    // Assert
    expect(action).toBeNull();
  });
});

describe("isOpenPaletteShortcut", () => {
  it("opens on / outside a text field", () => {
    // Arrange
    const event = plainKey("/");
    // Act
    const opens = isOpenPaletteShortcut(event, false);
    // Assert
    expect(opens).toBe(true);
  });

  it("does not steal / while typing in a text field", () => {
    // Arrange
    const event = plainKey("/");
    // Act
    const opens = isOpenPaletteShortcut(event, true);
    // Assert
    expect(opens).toBe(false);
  });

  it("opens on Cmd+K", () => {
    // Arrange
    const event = { ...plainKey("k"), metaKey: true };
    // Act
    const opens = isOpenPaletteShortcut(event, true);
    // Assert
    expect(opens).toBe(true);
  });

  it("yields Ctrl+K to a page handler that already claimed it", () => {
    // Arrange
    const event = { ...plainKey("k"), ctrlKey: true, defaultPrevented: true };
    // Act
    const opens = isOpenPaletteShortcut(event, false);
    // Assert
    expect(opens).toBe(false);
  });
});
