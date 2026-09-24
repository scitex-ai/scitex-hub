/**
 * Floating dock chat — panel geometry and the embedded chat URL.
 */

import { describe, expect, it } from "vitest";

import {
  embedUrl,
  maximizedRect,
  panelRect,
  toggleMaximized,
} from "@/components/_site-dock/chat-float";

describe("floating dock chat", () => {
  it("passes the page under the panel to the embedded chat", () => {
    expect(embedUrl("/apps/writer/", "Writer")).toBe(
      "/chat/?embed=1&ctx_path=%2Fapps%2Fwriter%2F&ctx_title=Writer",
    );
  });

  it("sits just above the dock at the dock's width on a phone", () => {
    const dock = { left: 10, top: 700, width: 370, height: 130 };
    expect(panelRect(dock, { width: 390, height: 844 })).toEqual({
      left: 10,
      top: 270,
      width: 370,
      height: 422,
    });
  });

  it("matches the launcher width with aligned left edges on desktop", () => {
    // Launcher 632 wide at left 324 on a 1280 viewport.
    const dock = { left: 324, top: 640, width: 632, height: 150 };
    const rect = panelRect(dock, { width: 1280, height: 800 });
    expect(rect.width).toBe(632);
    expect(rect.left).toBe(324);
    expect(rect.top).toBe(640 - 8 - rect.height);
  });

  it("a parked (left) launcher gets a same-width aligned panel", () => {
    const dock = { left: 8, top: 640, width: 500, height: 150 };
    const rect = panelRect(dock, { width: 1280, height: 800 });
    expect(rect.width).toBe(500);
    expect(rect.left).toBe(8);
  });

  it("maximize then restore returns to the small size", () => {
    expect(toggleMaximized(toggleMaximized(false))).toBe(false);
  });

  it("maximized fills the phone viewport above the dock, 8px inset", () => {
    const dock = { left: 10, top: 700, width: 370, height: 130 };
    expect(maximizedRect(dock, { width: 390, height: 844 })).toEqual({
      left: 8,
      top: 8,
      width: 374,
      height: 684,
    });
  });
});
