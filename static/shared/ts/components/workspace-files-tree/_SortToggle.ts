/**
 * Sort Toggle - Toggle between name (A-Z) and mtime (recent first) sorting
 * Used by all workspace modules via sidebar header button
 */

import type { WorkspaceFilesTree } from "./WorkspaceFilesTree";
import type { SortMode } from "./types";

const SORT_KEY = "scitex-file-sort-mode";

export function getSavedSortMode(): SortMode {
  return (localStorage.getItem(SORT_KEY) as SortMode) || "name";
}

/** Initialize sort toggle button and wire up to tree */
export function initSortToggle(tree: WorkspaceFilesTree): void {
  const btn = document.getElementById("sort-toggle");
  if (!btn) return;

  const saved = getSavedSortMode();
  tree.setSortMode(saved);
  updateSortButton(btn, saved);

  btn.addEventListener("click", () => {
    const newMode = tree.toggleSortMode();
    localStorage.setItem(SORT_KEY, newMode);
    updateSortButton(btn, newMode);
  });
}

function updateSortButton(btn: HTMLElement, mode: SortMode): void {
  const icon = btn.querySelector("i");
  if (icon) {
    icon.className =
      mode === "mtime" ? "fas fa-clock" : "fas fa-sort-alpha-down";
  }
  btn.classList.toggle("active", mode === "mtime");
  btn.title =
    mode === "mtime" ? "Sort by name (A-Z)" : "Sort by recent (newest first)";
}
