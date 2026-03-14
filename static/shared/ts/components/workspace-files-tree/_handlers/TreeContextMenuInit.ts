/**
 * TreeContextMenuInit - Context menu initialization for file tree
 *
 * Responsibilities:
 * - Set up contextmenu event listener
 * - Determine if click is on item, folder, or root
 * - Extract git status from DOM
 *
 * Extracted from WorkspaceFilesTree.ts for single responsibility.
 */

import type { ContextMenuHandler } from "./ContextMenuHandler";

export function initContextMenu(
  container: HTMLElement,
  contextMenuHandler: ContextMenuHandler,
): void {
  container.addEventListener("contextmenu", (e) => {
    e.preventDefault();
    const target = e.target as HTMLElement;
    const item = target.closest(".wft-item[data-path]");

    if (item) {
      const path = item.getAttribute("data-path");
      const isDir =
        item.classList.contains("wft-folder") ||
        item.classList.contains("wft-root") ||
        path === "";

      const gitStatusCode = item.getAttribute("data-git-status");
      const gitStaged = item.getAttribute("data-git-staged") === "true";
      const gitStatus = gitStatusCode
        ? { status: gitStatusCode, staged: gitStaged }
        : undefined;

      contextMenuHandler.show(
        e.clientX,
        e.clientY,
        path || "",
        isDir,
        gitStatus,
      );
    } else {
      const treeArea = target.closest(".wft-tree, .workspace-files-tree");
      if (treeArea) {
        contextMenuHandler.showForRoot(e.clientX, e.clientY);
      }
    }
  });

  // Right-click on toolbar (stx-shell-sidebar__header) → show root context menu
  const sidebar = container.closest(".stx-shell-sidebar");
  const toolbar = sidebar?.querySelector(":scope > .stx-shell-sidebar__header");
  if (toolbar) {
    toolbar.addEventListener("contextmenu", (e) => {
      e.preventDefault();
      contextMenuHandler.showForRoot(
        (e as MouseEvent).clientX,
        (e as MouseEvent).clientY,
      );
    });
  }

  // Right-click on Recent pane entries → show file context menu
  document.addEventListener("repo-monitor:contextmenu", ((e: CustomEvent) => {
    const { path, x, y } = e.detail;
    // Show file context menu (not directory, no git status from monitor)
    contextMenuHandler.show(x, y, path, false, undefined);
  }) as EventListener);
}
