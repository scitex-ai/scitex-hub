/**
 * A single click (tap) on a file opens it; folders toggle on a single click.
 *
 * Site audit 2026-09-14 (D12): a single click only highlighted a file and
 * opening needed a double-click, which touch screens cannot do reliably.
 * Finder-on-touch / Google Drive behaviour: tap opens. Keyboard Enter is
 * unchanged (KeyboardHandlers).
 */

import { describe, it, expect } from "vitest";

import { EventHandlers } from "@/components/workspace-files-tree/_handlers/EventHandlers";
import type { TreeConfig } from "@/components/workspace-files-tree/types";
import type { TreeStateManager } from "@/components/workspace-files-tree/_TreeState";

interface Calls {
  opened: string[];
  toggled: string[];
  selected: string[];
}

function mountTree(): { container: HTMLElement; calls: Calls } {
  const calls: Calls = { opened: [], toggled: [], selected: [] };
  const container = document.createElement("div");
  container.innerHTML = `
    <div class="wft-tree">
      <div class="wft-item wft-folder" data-path="docs"><span class="wft-name">docs</span></div>
      <div class="wft-item wft-file" data-path="docs/AGENTS.md"><span class="wft-name">AGENTS.md</span></div>
    </div>`;
  document.body.appendChild(container);
  const stateManager = {
    clearSelection: () => {},
  } as unknown as TreeStateManager;
  const handlers = new EventHandlers(
    { mode: "hub" } as unknown as TreeConfig,
    stateManager,
    (path) => calls.toggled.push(path),
    (path) => calls.selected.push(path),
    (path) => calls.opened.push(path),
    () => {},
    () => {},
  );
  handlers.attachEventListeners(container);
  return { container, calls };
}

function click(el: Element, init: MouseEventInit = {}): void {
  el.dispatchEvent(
    new MouseEvent("click", { bubbles: true, button: 0, detail: 1, ...init }),
  );
}

describe("workspace files tree: single click opens", () => {
  it("opens a file on a single click", () => {
    // Arrange
    const { container, calls } = mountTree();
    const file = container.querySelector(".wft-file .wft-name")!;
    // Act
    click(file);
    // Assert
    expect(calls.opened).toEqual(["docs/AGENTS.md"]);
  });

  it("opens the file only once for a double click", () => {
    // Arrange
    const { container, calls } = mountTree();
    const file = container.querySelector(".wft-file .wft-name")!;
    // Act
    click(file, { detail: 1 });
    click(file, { detail: 2 });
    file.dispatchEvent(new MouseEvent("dblclick", { bubbles: true }));
    // Assert
    expect(calls.opened).toHaveLength(1);
  });

  it("does not open a file on a ctrl-click (multi-select)", () => {
    // Arrange
    const { container, calls } = mountTree();
    const file = container.querySelector(".wft-file .wft-name")!;
    // Act
    click(file, { ctrlKey: true });
    // Assert
    expect(calls.opened).toEqual([]);
  });

  it("toggles a folder on a single click", () => {
    // Arrange
    const { container, calls } = mountTree();
    const folder = container.querySelector(".wft-folder .wft-name")!;
    // Act
    click(folder);
    // Assert
    expect(calls.toggled).toEqual(["docs"]);
  });
});
