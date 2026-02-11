/**
 * Module Filter Buttons (W S V C R H F T E)
 * Per-module filter buttons matching the global nav organization.
 * Clicking the current app's button toggles filtering on/off.
 * Clicking another button switches the filter mode.
 * Filter state is shared across all modules via localStorage.
 */

import type { WorkspaceFilesTree } from "./WorkspaceFilesTree.ts";
import type { WorkspaceMode } from "./types.ts";

const STORAGE_KEY = "scitex-tree-filter-mode";

export function initModuleFilterButtons(
  tree: WorkspaceFilesTree,
  currentMode: WorkspaceMode,
): void {
  const container = document.getElementById("module-filter-buttons");
  if (!container) return;

  const buttons =
    container.querySelectorAll<HTMLButtonElement>(".module-filter-btn");

  // Always start with no filtering - lightbulb is OFF by default
  // Clean up any stale persisted value from previous behavior
  localStorage.removeItem(STORAGE_KEY);
  tree.setFilterMode("all");

  // Wire click handlers
  buttons.forEach((btn) => {
    btn.addEventListener("click", () => {
      const mode = btn.getAttribute("data-mode") as WorkspaceMode;
      const wasActive = btn.classList.contains("active");

      // Deactivate all
      buttons.forEach((b) => b.classList.remove("active"));

      if (wasActive) {
        // Toggle off = show all files
        tree.setFilterMode("all");
        localStorage.setItem(STORAGE_KEY, "all");
      } else {
        // Activate this mode
        btn.classList.add("active");
        tree.setFilterMode(mode);
        localStorage.setItem(STORAGE_KEY, mode);
      }
    });
  });
}

function activateButton(
  buttons: NodeListOf<HTMLButtonElement>,
  mode: string,
): void {
  buttons.forEach((btn) => {
    btn.classList.toggle("active", btn.getAttribute("data-mode") === mode);
  });
}
