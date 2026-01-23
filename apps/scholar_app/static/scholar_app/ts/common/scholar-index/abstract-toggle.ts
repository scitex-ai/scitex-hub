/**
 * Abstract Toggle Module
 *
 * Handles global abstract display mode (all, truncated, none) and toggle functionality.
 *
 * @module abstract-toggle
 */

/**
 * Apply global abstract mode to all papers
 * @param mode - The abstract display mode: "all", "truncated", or "none"
 */
export function applyGlobalAbstractMode(mode: string): void {
  const abstracts = document.querySelectorAll(
    ".abstract-preview",
  ) as NodeListOf<HTMLElement>;
  abstracts.forEach((abstract) => {
    abstract.classList.remove("mode-all", "mode-truncated", "mode-none");
    abstract.classList.add("mode-" + mode);
  });
}

/**
 * Initialize abstract toggle functionality
 * Sets up global toggle buttons and applies saved preferences
 */
export function initializeAbstractToggle(): void {
  const savedMode = localStorage.getItem("global_abstract_mode") || "truncated";

  // Set initial button state
  const toggleButtons = document.querySelectorAll(
    ".global-abstract-toggle",
  ) as NodeListOf<HTMLElement>;
  toggleButtons.forEach((btn) => {
    if (btn.dataset.mode === savedMode) {
      btn.classList.remove("btn-outline-secondary");
      btn.classList.add("btn-primary");
    }
  });

  // Apply saved mode to all existing abstracts
  applyGlobalAbstractMode(savedMode);

  // Add click handlers to toggle buttons
  toggleButtons.forEach((btn) => {
    btn.addEventListener("click", function () {
      const mode = this.dataset.mode || "truncated";

      // Update button states
      toggleButtons.forEach((b) => {
        b.classList.remove("btn-primary");
        b.classList.add("btn-outline-secondary");
      });
      this.classList.remove("btn-outline-secondary");
      this.classList.add("btn-primary");

      // Save mode and apply it
      localStorage.setItem("global_abstract_mode", mode);
      applyGlobalAbstractMode(mode);
    });
  });
}

// Auto-initialize on DOM ready
document.addEventListener("DOMContentLoaded", function () {
  console.log("[Abstract Toggle] Initializing...");
  initializeAbstractToggle();
  console.log("[Abstract Toggle] Initialization complete");
});
