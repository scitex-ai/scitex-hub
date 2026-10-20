/** A document may own one site dock; framed documents may own none. */

import { beforeEach, describe, expect, it } from "vitest";

import { enforceDockBoundary } from "@/components/_site-dock/dock-boundary";

function appendDockPair(label: string): HTMLElement {
  const dock = document.createElement("nav");
  dock.dataset.siteDock = "";
  dock.dataset.label = label;
  const panel = document.createElement("section");
  panel.dataset.dockChatPanel = "";
  panel.dataset.label = label;
  document.body.append(dock, panel);
  return dock;
}

describe("site dock document boundary", () => {
  beforeEach(() => {
    document.body.innerHTML = "";
  });

  it("keeps exactly one shell dock and one floating Chat host", () => {
    const first = appendDockPair("first");
    appendDockPair("recursive");

    expect(enforceDockBoundary(document, false)).toBe(first);
    expect(document.querySelectorAll("[data-site-dock]")).toHaveLength(1);
    expect(document.querySelectorAll("[data-dock-chat-panel]")).toHaveLength(1);
    expect(
      document.querySelector<HTMLElement>("[data-site-dock]")?.dataset.label,
    ).toBe("first");
  });

  it("removes shell dock mounts from every framed document", () => {
    appendDockPair("nested");

    expect(enforceDockBoundary(document, true)).toBeNull();
    expect(document.querySelectorAll("[data-site-dock]")).toHaveLength(0);
    expect(document.querySelectorAll("[data-dock-chat-panel]")).toHaveLength(0);
  });
});
