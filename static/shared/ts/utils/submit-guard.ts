/**
 * Double-submit guard for forms that create something server-side.
 *
 * Card: hub-signup-email-stripe-funnel-20260917. The payment step POSTs to the
 * billing provider to open a card-setup session, and the backend owner measured
 * that repeated clicks before the completion webhook can create DUPLICATE
 * customers/sessions. This is the client half: one submit per form, and a second
 * one from the same form is cancelled rather than sent.
 *
 * It replaces a page-inline handler that read `event` from an enclosing scope while
 * declaring no parameter (`function () { ... event.preventDefault() }`) — in a real
 * browser that is `window.event`, which is not guaranteed, so the guard could
 * silently fail to cancel the second submit. Extracted here so the behaviour is
 * unit-tested instead of hoped for; the SERVER still owns idempotency, this only
 * stops the obvious double click.
 *
 * Usage in a template: `<form method="post" data-submit-guard="true">`, optionally
 * `data-busy-label="Please wait…"` on the submit button.
 */

/** Attribute a template puts on a form to opt in. Not a dataset key. */
export const SUBMIT_GUARD_ATTR = "data-submit-guard";
/** Marks a form already wired, so re-scanning cannot stack handlers. */
const WIRED_ATTR = "data-submit-guard-wired";
/** dataset key (unprefixed — `dataset["data-…"]` is not a valid property name). */
const SUBMITTING_KEY = "submitting";

/** Wire one form. Idempotent: a form already wired is left alone. */
export function wireSubmitGuard(form: HTMLFormElement): void {
  if (form.hasAttribute(WIRED_ATTR)) return;
  form.setAttribute(WIRED_ATTR, "true");

  form.addEventListener("submit", (event: SubmitEvent) => {
    // A second submit from the same form never reaches the network.
    if (form.dataset[SUBMITTING_KEY] === "true") {
      event.preventDefault();
      return;
    }
    form.dataset[SUBMITTING_KEY] = "true";

    const button = form.querySelector<HTMLButtonElement>(
      'button[type="submit"], input[type="submit"]',
    );
    if (!button) return;

    const busyLabel = button.dataset.busyLabel;
    if (busyLabel) button.textContent = busyLabel;
    button.disabled = true;
  });
}

/** Wire every guarded form under `root` (defaults to the document when there is one). */
export function wireSubmitGuards(root?: ParentNode): void {
  const scope = root ?? (typeof document === "undefined" ? null : document);
  if (!scope) return;

  scope
    .querySelectorAll<HTMLFormElement>(`form[${SUBMIT_GUARD_ATTR}="true"]`)
    .forEach(wireSubmitGuard);
}

// Run on load, and for forms that arrive later (the shell swaps panes in place).
// `typeof` guards keep this quiet if the document goes away (jsdom teardown).
if (typeof document !== "undefined") {
  document.addEventListener("DOMContentLoaded", () => wireSubmitGuards());

  if (typeof MutationObserver !== "undefined") {
    new MutationObserver(() => wireSubmitGuards()).observe(
      document.documentElement,
      { childList: true, subtree: true },
    );
  }
}
