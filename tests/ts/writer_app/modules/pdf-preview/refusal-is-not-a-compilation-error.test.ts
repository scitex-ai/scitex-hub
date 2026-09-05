/**
 * The preview pane must not call an authorization refusal a compilation error.
 *
 * Operator, Telegram 2026-09-05 (msg 4898), with a screenshot:
 *   「scitex-writer でコンパイルできない問題直せたりしますか？」
 *
 * He was not looking at a compilation problem. The session was read-only
 * (0 of 4 visitor slots), the backend answered 403 with
 * reason "readonly-visitor", and the preview pane rendered:
 *
 *     ⚠  Compilation Error
 *        Read-only mode — sign up or log in to make changes. …
 *        Check the error output for details
 *
 * Both the heading and the footer are false. No compiler ran, so there is
 * no error output to check — and he did what the panel told him to do and
 * went hunting for a LaTeX bug in scitex-writer.
 *
 * The reason was never missing: CompilationHttpError has carried .reason,
 * .actions, .signupUrl and .loginUrl since 2026-08-17, and the FULL
 * compilation path already branches on it (CompilationFull.detailFor).
 * It died on the preview path, where `error.message` was taken and the
 * object dropped — so the panel could not tell a refusal from a crash even
 * though the object it came from knew exactly which it was.
 *
 * These tests assert at the level that failed: what the pane renders.
 */

import { describe, it, expect, beforeEach, afterEach } from "vitest";
import { PDFViewer } from "@writer_app/modules/pdf-preview/viewer";
import { CompilationHttpError } from "@writer_app/modules/_compilation/compilation-http-error";

/** The read-only visitor rejection, verbatim from the dev preview. */
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

const CONTAINER_ID = "pdf-preview-container";

function container(): HTMLElement {
  const el = document.getElementById(CONTAINER_ID);
  if (!el) throw new Error("container missing");
  return el;
}

function newViewer(): PDFViewer {
  return new PDFViewer(CONTAINER_ID, "dark", 1);
}

describe("the preview pane distinguishes a refusal from a failure", () => {
  beforeEach(() => {
    document.body.innerHTML = `<div id="${CONTAINER_ID}"></div>`;
  });

  afterEach(() => {
    document.body.innerHTML = "";
  });

  it("does NOT call a read-only refusal a compilation error", () => {
    const refusal = new CompilationHttpError(
      READONLY_403.error,
      403,
      READONLY_403,
    );

    newViewer().displayError(refusal);

    const html = container().innerHTML;
    expect(html).not.toContain("Compilation Error");
    // there is no compiler output behind a request that never reached one
    expect(html).not.toContain("Check the error output");
  });

  it("names the refusal and offers the way out the payload already carries", () => {
    const refusal = new CompilationHttpError(
      READONLY_403.error,
      403,
      READONLY_403,
    );

    newViewer().displayError(refusal);

    const html = container().innerHTML;
    expect(html).toContain("Read-Only Session");
    expect(html).toContain(READONLY_403.error);
    expect(html).toContain(READONLY_403.detail);
    // the pane told the user to sign up or log in and gave them no way to;
    // the urls were in the payload the whole time
    expect(html).toContain('href="/auth/signup/"');
    expect(html).toContain('href="/auth/login/"');
  });

  it("still calls a real compilation failure a compilation error", () => {
    newViewer().displayError("! Undefined control sequence. \\badmacro");

    const html = container().innerHTML;
    expect(html).toContain("Compilation Error");
    expect(html).toContain("Check the error output");
    expect(html).toContain("Undefined control sequence");
  });

  it("treats a non-refusal CompilationHttpError as a failure", () => {
    // 409 "busy" is a real compile-path answer, not an authorization refusal
    const busy = new CompilationHttpError(
      "Preview compile is busy for this section, please retry",
      409,
      { success: false, error: "busy" },
    );

    newViewer().displayError(busy);

    const html = container().innerHTML;
    expect(html).toContain("Compilation Error");
    expect(html).toContain("please retry");
  });

  it("escapes user-authored content instead of injecting it", () => {
    // A LaTeX error quotes the offending source line back verbatim, and that
    // line is written by whoever owns the manuscript.
    newViewer().displayError('! Undefined control sequence <img src=x onerror="boom">');

    const el = container();
    expect(el.querySelector("img")).toBeNull();
    expect(el.innerHTML).toContain("&lt;img");
  });
});
