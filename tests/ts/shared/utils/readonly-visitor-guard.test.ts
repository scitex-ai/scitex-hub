/**
 * Tests for static/shared/ts/utils/readonly-visitor-guard.ts
 * (card hub-visitor-ux-allapps — fail-loud readonly write toast)
 */

import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";

import {
  installReadonlyVisitorGuard,
  showReadonlyVisitorToast,
} from "@shared/utils/readonly-visitor-guard";

function jsonResponse(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json" },
  });
}

describe("readonly-visitor-guard", () => {
  let nativeFetch: typeof window.fetch;

  beforeEach(() => {
    nativeFetch = window.fetch;
    document.body.innerHTML = "";
  });

  afterEach(() => {
    window.fetch = nativeFetch;
    document.body.innerHTML = "";
    vi.restoreAllMocks();
  });

  it("renders a toast with Sign up, Log in and retry actions", () => {
    showReadonlyVisitorToast({});
    const toast = document.getElementById("readonly-visitor-toast");
    expect(toast?.textContent).toContain("Sign up");
    expect(toast?.textContent).toContain("Log in");
    expect(toast?.textContent).toContain("Retry later");
  });

  it("does not stack a second toast while one is visible", () => {
    showReadonlyVisitorToast({});
    showReadonlyVisitorToast({});
    const toasts = document.querySelectorAll("#readonly-visitor-toast");
    expect(toasts.length).toBe(1);
  });

  it("shows the toast when fetch resolves a structured readonly 403", async () => {
    window.fetch = vi
      .fn()
      .mockResolvedValue(
        jsonResponse(403, { reason: "readonly-visitor", error: "nope" }),
      );
    installReadonlyVisitorGuard();

    await window.fetch("/api/workspace/save-file/", { method: "POST" });

    expect(document.getElementById("readonly-visitor-toast")).not.toBeNull();
  });

  it("ignores 403 responses without the readonly reason", async () => {
    window.fetch = vi
      .fn()
      .mockResolvedValue(jsonResponse(403, { error: "Unauthorized" }));
    installReadonlyVisitorGuard();

    await window.fetch("/api/anything/");

    expect(document.getElementById("readonly-visitor-toast")).toBeNull();
  });

  it("returns the original response to the caller", async () => {
    window.fetch = vi
      .fn()
      .mockResolvedValue(jsonResponse(403, { reason: "readonly-visitor" }));
    installReadonlyVisitorGuard();

    const resp = await window.fetch("/api/workspace/save-file/");

    expect(resp.status).toBe(403);
  });
});

// EOF
