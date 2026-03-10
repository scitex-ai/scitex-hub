/**
 * Scholar Library - Entry Point
 *
 * Defers paper loading until the Library tab is actually visible,
 * avoiding an unnecessary network request on initial page load when
 * the user lands on a different tab.
 *
 * Survives AJAX partial re-injection: uses a document-level MutationObserver
 * to detect when #tab-library appears in the DOM (ES modules are cached by the
 * browser and not re-executed on re-injection, so we must watch document-level).
 */

import { initLibraryManager } from "./_library-manager";

let tabObserver: MutationObserver | null = null;

function attachTabObserver(tab: HTMLElement): void {
  tabObserver?.disconnect();
  if (tab.classList.contains("active")) {
    initLibraryManager();
  }
  tabObserver = new MutationObserver(() => {
    if (tab.classList.contains("active")) {
      initLibraryManager();
    }
  });
  tabObserver.observe(tab, { attributes: true, attributeFilter: ["class"] });
}

function setup(): void {
  const tab = document.getElementById("tab-library");
  if (tab) {
    attachTabObserver(tab);
    return;
  }
  // #tab-library not yet in DOM — watch for it being inserted (AJAX injection)
  const docObserver = new MutationObserver(() => {
    const t = document.getElementById("tab-library");
    if (t) {
      docObserver.disconnect();
      attachTabObserver(t);
    }
  });
  docObserver.observe(document.body, { childList: true, subtree: true });
}

// Also re-attach when Scholar partial is re-injected (custom event from workspace shell)
document.addEventListener("workspace:module-injected", (e) => {
  if ((e as CustomEvent).detail?.module === "scholar") {
    const tab = document.getElementById("tab-library");
    if (tab) attachTabObserver(tab);
  }
});

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", setup);
} else {
  setup();
}
