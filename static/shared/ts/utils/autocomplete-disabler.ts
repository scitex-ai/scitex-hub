/**
 * GLOBAL POLICY: Disable autocomplete by default.
 *
 * Prevents inappropriate autofill (e.g., username in repository name field).
 * To enable autocomplete on specific fields, add autocomplete="on", "email", etc.
 *
 * Extracted from global_body_scripts.html inline <script>.
 */

const VALID_AUTOCOMPLETE_VALUES = [
  "on",
  "email",
  "username",
  "current-password",
  "new-password",
  "name",
  "given-name",
  "family-name",
  "tel",
  "url",
  "street-address",
  "postal-code",
  "country",
  "cc-number",
  "cc-exp",
  "cc-csc",
];

function disableAutocompleteGlobally(): void {
  const forms = document.querySelectorAll("form");

  forms.forEach((form) => {
    const formAutocomplete = form.getAttribute("autocomplete");
    const formWantsAutocomplete =
      formAutocomplete && formAutocomplete !== "off";

    if (!formWantsAutocomplete) {
      form.setAttribute("autocomplete", "off");
    }

    const inputs = form.querySelectorAll<
      HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement
    >("input, textarea, select");
    inputs.forEach((input) => {
      const inputAutocomplete = input.getAttribute("autocomplete");
      const shouldPreserve =
        inputAutocomplete &&
        VALID_AUTOCOMPLETE_VALUES.includes(inputAutocomplete);

      if (!shouldPreserve) {
        input.setAttribute("autocomplete", "off");
        input.autocomplete = "off";
      }
    });
  });
}

// Run on page load
document.addEventListener("DOMContentLoaded", disableAutocompleteGlobally);

// Also run when content is dynamically added
if (window.MutationObserver) {
  const observer = new MutationObserver((mutations) => {
    mutations.forEach((mutation) => {
      if (mutation.addedNodes.length) {
        disableAutocompleteGlobally();
      }
    });
  });

  document.addEventListener("DOMContentLoaded", () => {
    observer.observe(document.body, {
      childList: true,
      subtree: true,
    });
  });
}
