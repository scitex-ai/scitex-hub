/**
 * Git Status Toggle - Toggle git status highlighting in file tree
 * Placed in sidebar toolbar next to hidden files toggle and module filter.
 */

import type { WorkspaceFilesTree } from "./WorkspaceFilesTree.ts";

const GIT_STATUS_KEY = "scitex-show-git-status";

/** Initialize git status toggle button and wire up to tree */
export function initGitStatusToggle(tree: WorkspaceFilesTree): void {
  const btn = document.getElementById("git-status-toggle");
  if (!btn) return;

  // Default to enabled (true) unless explicitly disabled
  const stored = localStorage.getItem(GIT_STATUS_KEY);
  const showGit = stored === null ? true : stored === "true";
  tree.setShowGitStatus(showGit);
  updateToggleButton(btn, showGit);

  btn.addEventListener("click", () => {
    const newState = tree.toggleGitStatus();
    localStorage.setItem(GIT_STATUS_KEY, String(newState));
    updateToggleButton(btn, newState);
  });
}

function updateToggleButton(btn: HTMLElement, showGit: boolean): void {
  btn.classList.toggle("active", showGit);
  btn.title = showGit ? "Hide git status" : "Show git status";
}
