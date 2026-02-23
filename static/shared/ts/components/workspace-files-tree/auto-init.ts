/**
 * Workspace Files Tree - Auto Init
 * Shared auto-initialization for all workspace modules.
 * Reads config from standardized #workspace-project-config element.
 * Modules can register custom handlers via window globals before DOMContentLoaded.
 */

import type { TreeItem, WorkspaceMode } from "./types.ts";
import { WorkspaceFilesTree } from "./WorkspaceFilesTree.ts";
import { initHiddenFilesToggle } from "./HiddenFilesToggle.ts";
import { initGitStatusToggle } from "./GitStatusToggle.ts";
import { initModuleFilterButtons } from "./ModuleFilterButtons.ts";
import { initSortToggle } from "./SortToggle.ts";
import { FilePreviewPanel } from "./FilePreviewPanel.ts";

declare global {
  interface Window {
    /** Custom file select handler (set by module before DOMContentLoaded) */
    scitexOnFileSelect?: (path: string, item: TreeItem) => void;
    /** Custom tree data loaded handler (set by module before DOMContentLoaded) */
    scitexOnTreeDataLoaded?: (data: TreeItem[]) => void;
    /** Shared tree instance (set by auto-init after initialization) */
    workspaceFilesTree?: WorkspaceFilesTree;
  }
}

export async function autoInitWorkspaceTree(): Promise<WorkspaceFilesTree | null> {
  const configEl = document.getElementById("workspace-project-config");
  if (!configEl) return null;

  const username = configEl.dataset.username;
  const slug = configEl.dataset.slug;
  if (!username || !slug) return null;

  const mode = (configEl.dataset.mode || "hub") as WorkspaceMode;
  const containerId = configEl.dataset.container || "file-tree";

  // Skip if container element doesn't exist (e.g. three-column layout uses worktree pane instead)
  if (!document.getElementById(containerId)) return null;

  // Single click delegates to custom handler; default does nothing (dblclick navigates)
  const onFileSelect = window.scitexOnFileSelect || (() => {});

  const tree = new WorkspaceFilesTree({
    mode,
    containerId,
    username,
    slug,
    showFolderActions: true,
    showGitStatus: true,
    onFileSelect,
  });

  await tree.initialize();
  initHiddenFilesToggle(tree);
  initGitStatusToggle(tree);
  initSortToggle(tree);
  initModuleFilterButtons(tree, mode);

  window.workspaceFilesTree = tree;

  // Notify modules that tree is ready
  if (window.scitexOnTreeDataLoaded) {
    const data = tree.getTreeData?.() ?? [];
    window.scitexOnTreeDataLoaded(data);
  }

  return tree;
}

/**
 * Initialize WorkspaceFilesTree for [data-workspace-tree] elements.
 * Used by the three-column layout's shared worktree pane.
 * This path is separate from #workspace-project-config (used by hub/scholar/clew).
 */
export async function autoInitWorktreePanes(): Promise<void> {
  const panes = document.querySelectorAll<HTMLElement>("[data-workspace-tree]");
  if (panes.length === 0) return;

  for (const pane of panes) {
    // Ensure the element has an ID for WorkspaceFilesTree containerId
    if (!pane.id) {
      pane.id = "ws-worktree-tree";
    }

    const slug = pane.dataset.projectSlug;
    const username = pane.dataset.username;
    if (!slug || !username) continue;

    // Initialize file preview panel if present in DOM
    const previewEl = document.getElementById("ws-worktree-preview");
    let previewPanel: FilePreviewPanel | null = null;
    if (previewEl) {
      previewPanel = new FilePreviewPanel(previewEl);
      previewPanel.configure(username, slug);
      // Close button
      document
        .getElementById("ws-preview-close")
        ?.addEventListener("click", () => {
          previewPanel?.hide();
        });
    }

    // Delegate to custom handler if set; preview is handled via DOM event below
    const onFileSelect = window.scitexOnFileSelect || (() => {});

    const tree = new WorkspaceFilesTree({
      mode: "hub" as WorkspaceMode,
      containerId: pane.id,
      username,
      slug,
      showFolderActions: true,
      showGitStatus: true,
      onFileSelect,
    });

    await tree.initialize();

    // Preview panel: listen via DOM event so it persists even when modules replace onFileSelect
    if (previewPanel) {
      pane.addEventListener("file-select", ((e: CustomEvent) => {
        const path = e.detail?.path;
        if (path) previewPanel!.show(path);
      }) as EventListener);
    }
    initHiddenFilesToggle(tree);
    initGitStatusToggle(tree);
    initSortToggle(tree);
    initModuleFilterButtons(tree, "hub");

    window.workspaceFilesTree = tree;

    // Notify modules that tree is ready
    if (window.scitexOnTreeDataLoaded) {
      const data = tree.getTreeData?.() ?? [];
      window.scitexOnTreeDataLoaded(data);
    }
  }
}

// Auto-run on DOMContentLoaded
if (typeof document !== "undefined") {
  document.addEventListener("DOMContentLoaded", () => {
    // Primary init: module-owned trees via #workspace-project-config (hub, scholar, clew)
    autoInitWorkspaceTree();
    // Secondary init: shared worktree pane in three-column layout via [data-workspace-tree]
    autoInitWorktreePanes();
  });
}
