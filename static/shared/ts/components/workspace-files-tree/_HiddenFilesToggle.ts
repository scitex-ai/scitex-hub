/**
 * Hidden Files Toggle - Shared utility for dotfile visibility toggle
 * Used by all workspace modules (Scholar, Console, Vis, Writer)
 */

import type { WorkspaceFilesTree } from "./WorkspaceFilesTree";

const HIDDEN_FILES_KEY = "scitex-show-hidden-files";

/** Initialize hidden files toggle button and wire up to tree */
export function initHiddenFilesToggle(tree: WorkspaceFilesTree): void {
  const btn = document.getElementById("hidden-files-toggle");
  if (!btn) return;

  const stored = localStorage.getItem(HIDDEN_FILES_KEY) === "true";
  tree.setShowHidden(stored);
  updateToggleButton(btn, stored);

  btn.addEventListener("click", () => {
    const newState = tree.toggleHiddenFiles();
    localStorage.setItem(HIDDEN_FILES_KEY, String(newState));
    updateToggleButton(btn, newState);
  });
}

function updateToggleButton(btn: HTMLElement, showHidden: boolean): void {
  const icon = btn.querySelector("i");
  if (icon) {
    icon.className = showHidden ? "fas fa-eye" : "fas fa-eye-slash";
  }
  btn.classList.toggle("active", showHidden);
  btn.title = showHidden ? "Hide hidden files" : "Show hidden files";
}
