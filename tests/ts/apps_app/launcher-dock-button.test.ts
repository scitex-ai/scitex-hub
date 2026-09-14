/**
 * A grid app dragged into the dock gets the same caption as the server-rendered
 * dock buttons (operator, 2026-09-14: icon-only dock buttons were unreadable).
 */

import { describe, expect, it } from "vitest";

import { dockButtonFromTile } from "@apps_app/_launcher/dock-editor";

function tile(name: string): HTMLElement {
  const el = document.createElement("a");
  el.href = "/apps/writer/";
  el.dataset.module = "writer";
  el.dataset.category = "writing";
  el.innerHTML = `<span class="launcher-tile-icon"><i class="fas fa-pen"></i></span><span class="launcher-tile-name">${name}</span>`;
  return el;
}

describe("dockButtonFromTile", () => {
  it("captions the dock button with the tile's name", () => {
    // Arrange
    const source = tile("Writer");
    // Act
    const button = dockButtonFromTile(source);
    // Assert
    expect(button.querySelector(".site-dock-app-label")?.textContent).toBe(
      "Writer",
    );
  });
});
