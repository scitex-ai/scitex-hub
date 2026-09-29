/**
 * submit-guard — a second submit from the same form must be cancelled.
 *
 * Card: hub-signup-email-stripe-funnel-20260917. Written because the guard lived in
 * a page-inline handler that called `event.preventDefault()` while declaring no
 * parameter: in a real browser that resolves to `window.event`, which is not
 * guaranteed, so a double click could still reach the network and (per the backend
 * owner's measurement) create duplicate provider customers/sessions.
 *
 * This is the regression for that path: dispatch two submits and prove the second
 * one is prevented, with the first still allowed to go through.
 */

import { beforeEach, describe, expect, it, vi } from "vitest";

import {
  SUBMIT_GUARD_ATTR,
  wireSubmitGuard,
  wireSubmitGuards,
} from "@shared/utils/submit-guard";

function makeForm({ guarded = true, withButton = true } = {}) {
  const form = document.createElement("form");
  form.method = "post";
  if (guarded) form.setAttribute(SUBMIT_GUARD_ATTR, "true");
  if (withButton) {
    const button = document.createElement("button");
    button.type = "submit";
    button.textContent = "Continue to secure Stripe";
    form.appendChild(button);
  }
  document.body.appendChild(form);
  return form;
}

/** Dispatch a submit and report whether the event was cancelled. */
function submit(form: HTMLFormElement): { prevented: boolean } {
  const event = new Event("submit", { bubbles: true, cancelable: true });
  const spy = vi.spyOn(event, "preventDefault");
  form.dispatchEvent(event);
  return { prevented: spy.mock.calls.length > 0 };
}

describe("wireSubmitGuard", () => {
  beforeEach(() => {
    document.body.innerHTML = "";
  });

  it("lets the first submit through and disables the button", () => {
    const form = makeForm();
    wireSubmitGuard(form);
    const button = form.querySelector("button")!;

    const first = submit(form);

    expect(first.prevented).toBe(false);
    expect(button.disabled).toBe(true);
  });

  it("cancels the second submit from the same form", () => {
    const form = makeForm();
    wireSubmitGuard(form);

    const first = submit(form);
    const second = submit(form);

    expect(first.prevented).toBe(false);
    expect(second.prevented).toBe(true);
  });

  it("cancels every later attempt, not just the one after the first", () => {
    const form = makeForm();
    wireSubmitGuard(form);

    submit(form);
    const third = submit(form);
    const fourth = submit(form);

    expect(third.prevented).toBe(true);
    expect(fourth.prevented).toBe(true);
  });

  it("uses the button's busy label when it has one", () => {
    const form = makeForm();
    const button = form.querySelector("button")!;
    button.dataset.busyLabel = "Opening secure checkout…";
    wireSubmitGuard(form);

    submit(form);

    expect(button.textContent).toBe("Opening secure checkout…");
  });

  it("is idempotent — re-wiring does not cancel the first submit", () => {
    const form = makeForm();
    wireSubmitGuard(form);
    wireSubmitGuard(form);

    expect(submit(form).prevented).toBe(false);
  });

  it("leaves an unguarded form alone", () => {
    const form = makeForm({ guarded: false });
    wireSubmitGuards(document);

    expect(submit(form).prevented).toBe(false);
    expect(form.querySelector("button")!.disabled).toBe(false);
  });

  it("does not throw when a guarded form has no submit button", () => {
    const form = makeForm({ withButton: false });
    wireSubmitGuard(form);

    expect(() => submit(form)).not.toThrow();
    expect(submit(form).prevented).toBe(true);
  });

  it("wireSubmitGuards wires every guarded form it can see", () => {
    const a = makeForm();
    const b = makeForm();
    wireSubmitGuards(document);

    submit(a);
    submit(b);
    expect(submit(a).prevented).toBe(true);
    expect(submit(b).prevented).toBe(true);
  });
});
