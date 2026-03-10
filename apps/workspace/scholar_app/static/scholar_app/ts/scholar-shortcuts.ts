/**
 * Scholar Keyboard Shortcuts Modal
 *
 * Handles the keyboard shortcuts modal display/hide behavior.
 * Listens for workspace:module-injected for AJAX injection contexts.
 *
 * @module scholar-shortcuts
 */

function initScholarShortcuts(): void {
  const shortcutsBtn = document.getElementById("scholar-shortcuts-btn");
  const shortcutsModal = document.getElementById("scholar-shortcuts-modal");
  if (!shortcutsBtn || !shortcutsModal) return;

  shortcutsBtn.addEventListener("click", function () {
    shortcutsModal.style.display = "block";
  });

  // Close button
  const closeBtn = document.getElementById("scholar-shortcuts-close");
  if (closeBtn) {
    closeBtn.addEventListener("click", function () {
      shortcutsModal.style.display = "none";
    });
  }

  // Close on click outside modal content
  shortcutsModal.addEventListener("click", function (e: MouseEvent) {
    if (e.target === shortcutsModal) {
      shortcutsModal.style.display = "none";
    }
  });

  // Close on Escape key
  document.addEventListener("keydown", function (e: KeyboardEvent) {
    if (e.key === "Escape" && shortcutsModal.style.display === "block") {
      shortcutsModal.style.display = "none";
    }
  });
}

// Initialize on DOMContentLoaded
if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", initScholarShortcuts);
} else {
  initScholarShortcuts();
}

// Re-initialize when module is injected via AJAX
window.addEventListener("workspace:module-injected", initScholarShortcuts);

export { initScholarShortcuts };
