/**
 * File Table Hidden Files Sync
 * Syncs the sidebar's hidden files toggle with the main file browser table.
 * Reads from the same localStorage key used by the sidebar tree's HiddenFilesToggle.
 */

const HIDDEN_FILES_KEY = "scitex-show-hidden-files";

function syncTableHiddenFiles(): void {
  const showHidden = localStorage.getItem(HIDDEN_FILES_KEY) === "true";
  const rows = document.querySelectorAll<HTMLElement>(".file-browser-row");

  rows.forEach((row) => {
    const path = row.dataset.path || "";
    const name = path.split("/").pop() || "";
    if (name.startsWith(".")) {
      row.style.display = showHidden ? "" : "none";
    }
  });
}

document.addEventListener("DOMContentLoaded", () => {
  // Initial sync on page load
  syncTableHiddenFiles();

  // Listen for toggle button clicks (shared with sidebar tree)
  const toggleBtn = document.getElementById("hidden-files-toggle");
  if (toggleBtn) {
    toggleBtn.addEventListener("click", () => {
      // Small delay to let the sidebar tree's handler update localStorage first
      setTimeout(syncTableHiddenFiles, 50);
    });
  }

  // Sync across tabs via storage event
  window.addEventListener("storage", (e) => {
    if (e.key === HIDDEN_FILES_KEY) {
      syncTableHiddenFiles();
    }
  });
});
