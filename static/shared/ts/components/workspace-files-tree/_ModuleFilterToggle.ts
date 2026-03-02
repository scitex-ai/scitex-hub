/**
 * Module Filter Toggle - Shared utility for module-specific filtering toggle
 * When enabled (default): files outside the module's directories are grayed out
 * When disabled: all files shown equally (no inactive/grayed state)
 */

import type { WorkspaceFilesTree } from "./WorkspaceFilesTree";

const MODULE_FILTER_KEY = "scitex-module-filter-enabled";

/** Initialize module filter toggle button and wire up to tree */
export function initModuleFilterToggle(tree: WorkspaceFilesTree): void {
  const btn = document.getElementById("module-filter-toggle");
  if (!btn) return;

  // Default to disabled (false) if not stored — show all files by default
  const stored = localStorage.getItem(MODULE_FILTER_KEY);
  const enabled = stored === null ? false : stored === "true";
  tree.setModuleFilterEnabled(enabled);
  updateToggleButton(btn, enabled);

  btn.addEventListener("click", () => {
    const newState = tree.toggleModuleFilter();
    localStorage.setItem(MODULE_FILTER_KEY, String(newState));
    updateToggleButton(btn, newState);
  });
}

function updateToggleButton(btn: HTMLElement, enabled: boolean): void {
  btn.classList.toggle("active", enabled);
  btn.title = enabled
    ? "Show all files (disable module filter)"
    : "Focus on module files (enable module filter)";
}
