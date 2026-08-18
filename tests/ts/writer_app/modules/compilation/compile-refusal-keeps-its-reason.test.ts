/**
 * A refused compile must tell the user why it was refused.
 *
 * Operator, Telegram 2026-08-17 (msg 3456):
 *   「ライターで原稿ができていると言うことですけど、プレビューのコンパイルと
 *     フルのコンパ両方通りますか？エラーの時に正しくエラーの内容が出ますか？」
 *
 * The second half of that question was answered "no" by three lines in
 * compilation-api.ts:
 *
 *     if (!response.ok) throw new Error(`HTTP ${response.status}`);
 *
 * — one in compilePreview, one in compileFull, one in getStatus. None of
 * them read the body. These are the bodies the backend was actually
 * sending, measured on live scitex.ai the same day; every one of them was
 * discarded and replaced with a three-digit number.
 *
 * The tests below assert at the level that failed: what the panel is
 * handed. `HTTP 403` is not a reason; `HTTP 409` ("please retry") is
 * actively misleading.
 */

import { describe, it, expect, beforeEach, afterEach } from "vitest";
import { CompilationAPI } from "@writer_app/modules/_compilation/compilation-api";
import { CompilationHttpError } from "@writer_app/modules/_compilation/compilation-http-error";
import { CompilationFull } from "@writer_app/modules/_compilation/compilation-full";
import { CompilationState } from "@writer_app/modules/_compilation/compilation-state";
import { CompilationUI } from "@writer_app/modules/_compilation/compilation-ui";
import { CompilationQueue } from "@writer_app/modules/_compilation/compilation-queue";

/** The read-only visitor rejection, verbatim from prod. */
const READONLY_403 = {
  error: "Read-only mode — sign up or log in to make changes.",
  reason: "readonly-visitor",
  detail:
    "Visitor slots are being prepared — you are browsing read-only. " +
    "Retry in a few minutes for a writable slot.",
  actions: ["signup", "login", "retry-later"],
  signup_url: "/auth/signup/",
  login_url: "/auth/login/",
};

const NOT_FOUND_404 = { success: false, error: "Project 123 not found" };

const BUSY_409 = {
  success: false,
  error: "Preview compile is busy for this section, please retry",
};

function jsonResponse(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

function htmlResponse(status: number): Response {
  return new Response("<html><body>502 Bad Gateway</body></html>", {
    status,
    headers: { "Content-Type": "text/html" },
  });
}

/** Answer every fetch with the same canned response. */
function stubFetch(make: () => Response): void {
  (globalThis as any).fetch = async () => make();
}

const OPTIONS = { projectId: 123, docType: "manuscript", content: "\\hello" };

describe("a refused compile keeps its reason", () => {
  const nativeFetch = globalThis.fetch;

  beforeEach(() => {
    document.body.innerHTML = "";
    document.documentElement.setAttribute("data-theme", "light");
  });

  afterEach(() => {
    globalThis.fetch = nativeFetch;
    document.body.innerHTML = "";
  });

  it("gives compileFull the 403 detail, not the status code", async () => {
    stubFetch(() => jsonResponse(403, READONLY_403));
    const api = new CompilationAPI();
    await expect(api.compileFull(OPTIONS as any)).rejects.toThrow(
      /Visitor slots are being prepared/,
    );
  });

  it("gives compilePreview the 403 detail too", async () => {
    stubFetch(() => jsonResponse(403, READONLY_403));
    const api = new CompilationAPI();
    await expect(api.compilePreview(OPTIONS as any)).rejects.toThrow(
      /Visitor slots are being prepared/,
    );
  });

  it("gives getStatus the 404 reason", async () => {
    stubFetch(() => jsonResponse(404, NOT_FOUND_404));
    const api = new CompilationAPI();
    await expect(api.getStatus(123, "job-1")).rejects.toThrow(
      /Project 123 not found/,
    );
  });

  it("says 'please retry' on the 409, not 'HTTP 409'", async () => {
    stubFetch(() => jsonResponse(409, BUSY_409));
    const api = new CompilationAPI();
    await expect(api.compilePreview(OPTIONS as any)).rejects.toThrow(
      /busy for this section, please retry/,
    );
  });

  it("no longer throws the bare status string for a JSON refusal", async () => {
    // Positive control for the four assertions above: they would also
    // pass if `HTTP 403` were merely *appended* to the reason. It is the
    // ABSENCE of the old message that proves the old code path is gone.
    stubFetch(() => jsonResponse(403, READONLY_403));
    const api = new CompilationAPI();
    let thrown: unknown;
    try {
      await api.compileFull(OPTIONS as any);
    } catch (error) {
      thrown = error;
    }
    expect((thrown as Error).message).not.toContain("HTTP 403");
  });

  it("preserves the machine-readable reason", async () => {
    stubFetch(() => jsonResponse(403, READONLY_403));
    const api = new CompilationAPI();
    const thrown = await api
      .compileFull(OPTIONS as any)
      .catch((error: unknown) => error);
    expect((thrown as CompilationHttpError).reason).toBe("readonly-visitor");
  });

  it("preserves the offered actions", async () => {
    stubFetch(() => jsonResponse(403, READONLY_403));
    const api = new CompilationAPI();
    const thrown = await api
      .compileFull(OPTIONS as any)
      .catch((error: unknown) => error);
    expect((thrown as CompilationHttpError).actions).toEqual([
      "signup",
      "login",
      "retry-later",
    ]);
  });

  it("preserves the signup url so the panel can offer Sign up", async () => {
    stubFetch(() => jsonResponse(403, READONLY_403));
    const api = new CompilationAPI();
    const thrown = await api
      .compileFull(OPTIONS as any)
      .catch((error: unknown) => error);
    expect((thrown as CompilationHttpError).signupUrl).toBe("/auth/signup/");
  });

  it("carries the status code for callers that branch on it", async () => {
    stubFetch(() => jsonResponse(409, BUSY_409));
    const api = new CompilationAPI();
    const thrown = await api
      .compilePreview(OPTIONS as any)
      .catch((error: unknown) => error);
    expect((thrown as CompilationHttpError).status).toBe(409);
  });

  it("still falls back to the status when the body is not JSON", async () => {
    // A proxy 502 arrives as HTML. Inventing a reason for it would be
    // worse than the status code, so this path must NOT change.
    stubFetch(() => htmlResponse(502));
    const api = new CompilationAPI();
    await expect(api.compileFull(OPTIONS as any)).rejects.toThrow("HTTP 502");
  });
});

/**
 * The end of the wire: what the compile panel is handed.
 *
 * `CompilationUI.showError` forwards to `window.showCompilationError`,
 * which is how the panel/modal renders. Asserting on the API's thrown
 * Error alone would not prove the reason survives the catch block in
 * CompilationFull — which used to pass a JS stack as the body text.
 */
describe("the panel shows the reason the backend gave", () => {
  const nativeFetch = globalThis.fetch;
  let shown: { message: string; log: string } | null;

  beforeEach(() => {
    shown = null;
    (window as any).showCompilationError = (message: string, log: string) => {
      shown = { message, log };
    };
  });

  afterEach(() => {
    globalThis.fetch = nativeFetch;
    delete (window as any).showCompilationError;
    document.body.innerHTML = "";
  });

  function buildFull(): CompilationFull {
    const api = new CompilationAPI();
    const state = new CompilationState();
    const ui = new CompilationUI();
    return new CompilationFull(
      api,
      state,
      ui,
      new CompilationQueue(api, state, ui),
    );
  }

  it("puts the 403 detail in front of the user", async () => {
    stubFetch(() => jsonResponse(403, READONLY_403));
    await buildFull().compile(OPTIONS as any);
    const rendered = `${shown?.message ?? ""}\n${shown?.log ?? ""}`;
    expect(rendered).toContain("Visitor slots are being prepared");
  });

  it("offers the signup url in the panel body for a read-only refusal", async () => {
    stubFetch(() => jsonResponse(403, READONLY_403));
    await buildFull().compile(OPTIONS as any);
    expect(shown?.log ?? "").toContain("/auth/signup/");
  });

  it("does not show the user a bare status code", async () => {
    stubFetch(() => jsonResponse(403, READONLY_403));
    await buildFull().compile(OPTIONS as any);
    expect(shown?.message ?? "").not.toContain("HTTP 403");
  });

  it("still shows something when the body is not JSON", async () => {
    // Control: the panel must never be handed an empty headline.
    stubFetch(() => htmlResponse(502));
    await buildFull().compile(OPTIONS as any);
    expect(shown?.message ?? "").toContain("HTTP 502");
  });
});

// EOF
