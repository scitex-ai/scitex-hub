/**
 * Project Selector Handler for Scholar App
 *
 * Writes go through the shared project-context module so every reader
 * resolves one normalized value. On load, seeds the stored selection from
 * the server-rendered `<select>` value or `?project=` — a server-rendered
 * `selected` option fires no change event, which used to leave the stored
 * selection empty ("No project selected") with a project visibly chosen.
 */

import {
  PROJECT_STORAGE_KEY,
  getSelectedProjectId,
  setSelectedProjectId,
} from "./_project-context";

function initProjectSelector(): void {
  const projectSelector = document.getElementById(
    "project-selector",
  ) as HTMLSelectElement | null;

  if (projectSelector) {
    // Store selected project in sessionStorage for use by save functions
    projectSelector.addEventListener(
      "change",
      function (this: HTMLSelectElement): void {
        setSelectedProjectId(this.value || null);
        if (this.value) {
          console.log("[Scholar] Selected project ID:", this.value);
        } else {
          console.log("[Scholar] Cleared project selection");
        }
      },
    );

    // Seed from the server-rendered value / URL when nothing stored yet.
    // getSelectedProjectId() falls back to this very select, so a stored
    // value always exists afterwards when a project is visibly selected.
    const resolved = getSelectedProjectId();
    if (resolved) {
      projectSelector.value = resolved;
    } else {
      try {
        sessionStorage.removeItem(PROJECT_STORAGE_KEY);
      } catch {
        /* ignore */
      }
    }
  }
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", function () {
    initProjectSelector();
  });
} else {
  initProjectSelector();
}
