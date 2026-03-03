/**
 * Global: Prevent Enter key from submitting forms & route Enter to action buttons.
 *
 * 1. Block non-POST form submissions (JS-driven forms should not reload).
 * 2. Enter key in any input → find & click the nearest action button with visual feedback.
 *
 * Extracted from global_body_scripts.html inline <script>.
 */

// 1. Block non-POST form submissions
document.addEventListener(
  "submit",
  (e: Event) => {
    const form = e.target as HTMLFormElement;
    if (form.tagName !== "FORM") return;
    const method = (form.getAttribute("method") || "").toLowerCase();
    if (method === "post") return;
    e.preventDefault();
  },
  true,
);

// 2. Enter key → find & click nearest action button
document.addEventListener(
  "keydown",
  (e: KeyboardEvent) => {
    if (e.key !== "Enter") return;
    const el = e.target as HTMLElement;
    if (!el || (el.tagName !== "INPUT" && el.tagName !== "SELECT")) return;
    if (el.tagName === "TEXTAREA") return;

    e.preventDefault();

    // Find action button: same wrapper first, then form-level submit/primary button
    let btn: HTMLButtonElement | null = null;
    const wrapper = el.closest(".input-wrapper, .input-group");
    if (wrapper) {
      btn = wrapper.querySelector(
        'button[type="submit"], button.btn-build, button.btn-primary, button.search-btn',
      );
    }
    if (!btn) {
      const form = el.closest("form");
      if (form) {
        btn =
          form.querySelector('button[type="submit"]') ||
          form.querySelector(
            "button.btn-build, button.btn-primary, button.search-btn",
          );
      }
    }
    if (!btn) return;

    // Visual feedback
    btn.classList.remove("btn--enter-pressed");
    void btn.offsetWidth; // Force reflow to restart animation
    btn.classList.add("btn--enter-pressed");
    btn.addEventListener("animationend", function handler() {
      btn!.classList.remove("btn--enter-pressed");
      btn!.removeEventListener("animationend", handler);
    });

    btn.click();
  },
  true,
);
