/** Secure navigation bridge between floating Chat and its parent page. */

import { describe, expect, it, vi } from "vitest";

import {
  EMBED_PARENT_NAVIGATION,
  parentNavigationPath,
  postParentNavigation,
  trustedParentNavigationPath,
} from "@/components/_site-dock/embed-navigation";

const ORIGIN = "https://scitex.ai";
const SETTINGS = "/accounts/settings/ai-providers/";

describe("embedded chat parent navigation", () => {
  it("accepts only the AI provider settings path on the current origin", () => {
    expect(
      parentNavigationPath(
        `${SETTINGS}?next=%2Fchat%2F#anthropic`,
        ORIGIN,
      ),
    ).toBe(`${SETTINGS}?next=%2Fchat%2F#anthropic`);

    expect([
      parentNavigationPath("https://attacker.example/steal", ORIGIN),
      parentNavigationPath("//attacker.example/steal", ORIGIN),
      parentNavigationPath("javascript:alert(1)", ORIGIN),
      parentNavigationPath("/accounts/settings/ai-providers.evil/", ORIGIN),
      parentNavigationPath("/accounts/settings/profile/", ORIGIN),
    ]).toEqual([null, null, null, null, null]);
  });

  it("rejects cross-origin and untrusted-frame messages", () => {
    const trustedFrame = {} as WindowProxy;
    const otherFrame = {} as WindowProxy;
    const data = { type: EMBED_PARENT_NAVIGATION, href: SETTINGS };

    expect(
      trustedParentNavigationPath(
        { source: trustedFrame, origin: ORIGIN, data } as MessageEvent,
        trustedFrame,
        ORIGIN,
      ),
    ).toBe(SETTINGS);
    expect(
      trustedParentNavigationPath(
        { source: otherFrame, origin: ORIGIN, data } as MessageEvent,
        trustedFrame,
        ORIGIN,
      ),
    ).toBeNull();
    expect(
      trustedParentNavigationPath(
        { source: trustedFrame, origin: "https://attacker.example", data } as MessageEvent,
        trustedFrame,
        ORIGIN,
      ),
    ).toBeNull();
  });

  it("posts the typed settings command only from an embedded window", () => {
    const postMessage = vi.fn();
    const parent = { postMessage };
    const embeddedWindow = {
      location: { origin: ORIGIN },
      parent,
    };

    expect(postParentNavigation(SETTINGS, embeddedWindow)).toBe(true);
    expect(postMessage).toHaveBeenCalledWith(
      { type: EMBED_PARENT_NAVIGATION, href: SETTINGS },
      ORIGIN,
    );

    const topWindow = {
      location: { origin: ORIGIN },
      parent: null as unknown,
    };
    topWindow.parent = topWindow;
    expect(postParentNavigation(SETTINGS, topWindow)).toBe(false);
  });
});
