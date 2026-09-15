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
